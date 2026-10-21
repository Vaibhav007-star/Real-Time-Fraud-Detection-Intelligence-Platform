from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import settings
from app.schemas.transaction import TransactionCreate

try:
    import networkx as nx  # type: ignore
    NETWORKX_INSTALLED = True
except ImportError:
    NETWORKX_INSTALLED = False


class GraphFraudIntelligenceEngine:
    """Real-time graph analytics engine modeling Accounts, Devices, IPs, Merchants, and Transactions.

    Maintains typed nodes and edges with bounded memory, lookback window pruning, and bounded
    traversal depth. Computes explainable graph signals (shared-device rings, IP sharing,
    repeated transfers, circular transfer cycles, neighborhood risk) without branding an entire
    connected component fraudulent simply because one neighbor has elevated risk.
    """

    def __init__(
        self,
        max_nodes: Optional[int] = None,
        lookback_seconds: Optional[int] = None,
        max_traversal_depth: Optional[int] = None,
    ) -> None:
        self.max_nodes = max_nodes or settings.graph_max_nodes
        self.lookback_seconds = lookback_seconds or settings.graph_lookback_seconds
        self.max_traversal_depth = max_traversal_depth or settings.graph_max_traversal_depth

        # Typed node storage: node_id -> metadata dict
        self.nodes: Dict[str, Dict[str, Any]] = {}
        # Adjacency: u -> v -> edge metadata dict
        self.adj: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        self.undirected_adj: Dict[str, Set[str]] = defaultdict(set)

        # Fast relational indexes for streaming graph features
        self.device_to_accounts: Dict[str, Set[str]] = defaultdict(set)
        self.ip_to_accounts: Dict[str, Set[str]] = defaultdict(set)
        self.account_to_devices: Dict[str, Set[str]] = defaultdict(set)
        self.transfer_out_edges: Dict[str, Dict[str, List[Tuple[datetime, float, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.entity_recent_connections: Dict[str, Deque[datetime]] = defaultdict(lambda: deque(maxlen=100))

    def _upsert_node(
        self, node_id: str, node_type: str, timestamp: str, risk_score: float = 0.05, **attrs: Any
    ) -> None:
        if node_id not in self.nodes:
            if len(self.nodes) >= self.max_nodes:
                # Evict oldest TRANSACTION node first to preserve structural entity nodes
                tx_keys = [k for k, v in self.nodes.items() if v.get("node_type") == "TRANSACTION"]
                evict_key = tx_keys[0] if tx_keys else next(iter(self.nodes))
                self._remove_node(evict_key)
            self.nodes[node_id] = {
                "id": node_id,
                "node_type": node_type,
                "first_seen": timestamp,
                "last_seen": timestamp,
                "risk_score": round(float(risk_score), 4),
                "tx_count": 1,
                **attrs,
            }
        else:
            entry = self.nodes[node_id]
            entry["last_seen"] = timestamp
            entry["tx_count"] = int(entry.get("tx_count", 0)) + 1
            # Exponential moving average + peak retention for entity risk
            entry["risk_score"] = round(
                max(float(entry.get("risk_score", 0.05)) * 0.85, float(risk_score)), 4
            )
            for k, v in attrs.items():
                if v is not None:
                    entry[k] = v

    def _remove_node(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)
        neighbors = list(self.undirected_adj.pop(node_id, set()))
        for nb in neighbors:
            self.undirected_adj[nb].discard(node_id)
            self.adj[nb].pop(node_id, None)
        self.adj.pop(node_id, None)

    def _upsert_edge(
        self, source: str, target: str, edge_type: str, timestamp: str, amount: float = 0.0
    ) -> None:
        existing = self.adj[source].get(target)
        if existing is None:
            self.adj[source][target] = {
                "source": source,
                "target": target,
                "edge_type": edge_type,
                "first_seen": timestamp,
                "last_seen": timestamp,
                "count": 1,
                "total_amount": round(float(amount), 2),
            }
        else:
            existing["last_seen"] = timestamp
            existing["count"] = int(existing["count"]) + 1
            existing["total_amount"] = round(float(existing["total_amount"]) + float(amount), 2)
        self.undirected_adj[source].add(target)
        self.undirected_adj[target].add(source)

    def analyze_and_record_transaction(
        self, tx: TransactionCreate
    ) -> Tuple[Dict[str, float], float, List[str]]:
        """Analyzes graph relationships for `tx`, updates graph state, and returns:
        (graph_feature_dict, normalized_graph_risk_score, explainable_graph_reasons).
        """
        event_dt = datetime.fromisoformat(tx.timestamp)
        ts_iso = tx.timestamp
        acc_id = tx.source_account_id
        dev_id = tx.device_id
        ip_id = f"IP:{tx.ip_address}"
        merch_id = tx.merchant_id or "MERCH-UNKNOWN"
        dst_acc = tx.destination_account_id

        # Record connection associations before scoring current topology
        self.device_to_accounts[dev_id].add(acc_id)
        self.ip_to_accounts[ip_id].add(acc_id)
        self.account_to_devices[acc_id].add(dev_id)
        self.entity_recent_connections[acc_id].append(event_dt)
        self.entity_recent_connections[dev_id].append(event_dt)

        if dst_acc:
            self.transfer_out_edges[acc_id][dst_acc].append((event_dt, tx.transaction_amount, tx.transaction_id))

        # 1. Shared-device & shared-IP cluster detection
        shared_dev_accounts = sorted(self.device_to_accounts[dev_id])
        shared_ip_accounts = sorted(self.ip_to_accounts[ip_id])
        dev_acc_count = len(shared_dev_accounts)
        ip_acc_count = len(shared_ip_accounts)

        # 2. Repeated transfers & Circular transfer detection (bounded depth <= 4)
        repeated_transfers = 0
        has_circular_path = 0.0
        circular_chain_desc: Optional[str] = None
        short_transfer_chain_len = 0

        if dst_acc:
            # Prune transfer edges older than lookback window
            history_list = [
                item
                for item in self.transfer_out_edges[acc_id][dst_acc]
                if abs((event_dt - item[0]).total_seconds()) <= self.lookback_seconds
            ]
            self.transfer_out_edges[acc_id][dst_acc] = history_list
            repeated_transfers = len(history_list)

            # BFS from dst_acc to see if there is a directed transfer path back to acc_id (cycle!)
            queue: Deque[Tuple[str, List[str]]] = deque([(dst_acc, [acc_id, dst_acc])])
            visited_in_bfs: Set[str] = {dst_acc}
            while queue:
                curr_acc, path = queue.popleft()
                if len(path) > 5:
                    continue
                for next_acc, edge_events in self.transfer_out_edges.get(curr_acc, {}).items():
                    recent_edges = [
                        e for e in edge_events if abs((event_dt - e[0]).total_seconds()) <= self.lookback_seconds
                    ]
                    if not recent_edges:
                        continue
                    if next_acc == acc_id:
                        has_circular_path = 1.0
                        circular_chain_desc = " -> ".join(path + [acc_id])
                        short_transfer_chain_len = len(path)
                        break
                    if next_acc not in visited_in_bfs and len(path) < 4:
                        visited_in_bfs.add(next_acc)
                        queue.append((next_acc, path + [next_acc]))
                if has_circular_path > 0:
                    break

        # 3. Local neighborhood risk (1-to-2 hop average with damping so innocent neighbors aren't auto-flagged)
        neighbor_risks: List[float] = []
        for nb in self.undirected_adj.get(acc_id, set()):
            if nb in self.nodes:
                neighbor_risks.append(float(self.nodes[nb].get("risk_score", 0.05)))
        for peer_acc in shared_dev_accounts:
            if peer_acc != acc_id and peer_acc in self.nodes:
                neighbor_risks.append(float(self.nodes[peer_acc].get("risk_score", 0.15)))

        local_neighborhood_risk = (
            sum(neighbor_risks) / len(neighbor_risks) if neighbor_risks else 0.05
        )

        # 4. Sudden increase in entity connections (degree velocity spike)
        recent_dev_conns = [
            dt for dt in self.entity_recent_connections[dev_id] if abs((event_dt - dt).total_seconds()) <= 300.0
        ]
        entity_degree_spike = min(1.0, max(0.0, (len(recent_dev_conns) - 2) / 6.0))

        # 5. Compute explainable graph risk score (0.0 to 1.0)
        explanations: List[str] = []
        score_components = 0.04

        if dev_acc_count >= 2:
            dev_contrib = min(0.45, 0.16 * (dev_acc_count - 1))
            score_components += dev_contrib
            peer_preview = ", ".join([a for a in shared_dev_accounts if a != acc_id][:4])
            explanations.append(
                f"Device '{dev_id}' is shared across {dev_acc_count} distinct accounts ({peer_preview})."
            )

        if ip_acc_count >= 3:
            ip_contrib = min(0.22, 0.06 * (ip_acc_count - 1))
            score_components += ip_contrib
            explanations.append(
                f"Network identifier '{tx.ip_address}' is shared by {ip_acc_count} accounts."
            )

        if has_circular_path > 0 and circular_chain_desc:
            score_components += 0.42
            explanations.append(
                f"Circular transfer ring detected across connected accounts: {circular_chain_desc}."
            )
        elif repeated_transfers >= 2 and dst_acc:
            rep_contrib = min(0.25, 0.09 * repeated_transfers)
            score_components += rep_contrib
            explanations.append(
                f"Repeated transfers ({repeated_transfers}x) from '{acc_id}' to destination '{dst_acc}'."
            )

        if local_neighborhood_risk >= 0.35:
            nb_contrib = min(0.20, (local_neighborhood_risk - 0.25) * 0.4)
            score_components += nb_contrib
            explanations.append(
                f"Elevated 1-2 hop neighborhood risk ({local_neighborhood_risk:.2f}) from connected entities."
            )

        if entity_degree_spike >= 0.35:
            score_components += 0.12 * entity_degree_spike
            explanations.append(
                f"Sudden connection velocity spike on device '{dev_id}' ({len(recent_dev_conns)} events in 5m)."
            )

        graph_score = round(min(0.99, max(0.01, score_components)), 4)

        # 6. Persist nodes and typed edges into the graph
        self._upsert_node(acc_id, "ACCOUNT", ts_iso, risk_score=graph_score, location=tx.location)
        self._upsert_node(dev_id, "DEVICE", ts_iso, risk_score=graph_score)
        self._upsert_node(ip_id, "IP", ts_iso, risk_score=graph_score, ip_subnet=tx.ip_address)
        self._upsert_node(
            tx.transaction_id,
            "TRANSACTION",
            ts_iso,
            risk_score=graph_score,
            amount=tx.transaction_amount,
            currency=tx.currency,
        )

        self._upsert_edge(acc_id, dev_id, "USES_DEVICE", ts_iso, tx.transaction_amount)
        self._upsert_edge(acc_id, ip_id, "CONNECTS_FROM_IP", ts_iso, tx.transaction_amount)
        self._upsert_edge(acc_id, tx.transaction_id, "ORIGINATES_TX", ts_iso, tx.transaction_amount)

        if tx.merchant_id:
            self._upsert_node(
                merch_id,
                "MERCHANT",
                ts_iso,
                risk_score=graph_score * 0.6,
                category=tx.merchant_category,
            )
            self._upsert_edge(acc_id, merch_id, "PAYS_MERCHANT", ts_iso, tx.transaction_amount)
            self._upsert_edge(tx.transaction_id, merch_id, "ASSOCIATED_WITH", ts_iso, tx.transaction_amount)

        if dst_acc:
            self._upsert_node(dst_acc, "ACCOUNT", ts_iso, risk_score=graph_score * 0.85)
            self._upsert_edge(acc_id, dst_acc, "TRANSFERS_TO", ts_iso, tx.transaction_amount)
            self._upsert_edge(tx.transaction_id, dst_acc, "ASSOCIATED_WITH", ts_iso, tx.transaction_amount)

        if not explanations:
            explanations.append(
                f"Account '{acc_id}' operates within normal isolated device/merchant topology (1 account on '{dev_id}')."
            )

        graph_features = {
            "device_shared_account_count": float(dev_acc_count),
            "ip_shared_account_count": float(ip_acc_count),
            "related_account_tx_count": float(sum(len(self.undirected_adj.get(a, set())) for a in shared_dev_accounts)),
            "repeated_transfer_count": float(repeated_transfers),
            "has_circular_transfer_path": float(has_circular_path),
            "short_transfer_chain_length": float(short_transfer_chain_len),
            "local_neighborhood_risk": round(local_neighborhood_risk, 4),
            "entity_degree_spike": round(entity_degree_spike, 4),
        }
        return graph_features, graph_score, explanations

    def get_entity_neighborhood(
        self,
        center_id: Optional[str] = None,
        max_depth: int = 2,
        node_types: Optional[List[str]] = None,
        max_nodes_returned: int = 60,
    ) -> Dict[str, Any]:
        """Returns a bounded subgraph around `center_id` (or highest-risk entities if None) for the Graph Explorer UI."""
        depth_limit = max(1, min(int(max_depth), self.max_traversal_depth))
        allowed_types = {t.upper() for t in node_types} if node_types else None

        if not self.nodes:
            return {
                "center_id": center_id,
                "nodes": [],
                "edges": [],
                "summary": {"node_count": 0, "edge_count": 0, "shared_devices": [], "suspicious_clusters": 0},
            }

        # Pick starting entity if none provided or not found
        if not center_id or center_id not in self.nodes:
            account_nodes = [
                (nid, data) for nid, data in self.nodes.items() if data.get("node_type") == "ACCOUNT"
            ]
            if account_nodes:
                account_nodes.sort(key=lambda item: float(item[1].get("risk_score", 0.0)), reverse=True)
                center_id = account_nodes[0][0]
            else:
                center_id = next(iter(self.nodes))

        visited_nodes: Set[str] = {center_id}
        queue: Deque[Tuple[str, int]] = deque([(center_id, 0)])

        while queue and len(visited_nodes) < max_nodes_returned:
            curr, d = queue.popleft()
            if d >= depth_limit:
                continue
            for nb in self.undirected_adj.get(curr, set()):
                if nb not in self.nodes:
                    continue
                nb_type = self.nodes[nb].get("node_type", "")
                if allowed_types and nb_type not in allowed_types and nb != center_id:
                    continue
                if nb not in visited_nodes:
                    visited_nodes.add(nb)
                    queue.append((nb, d + 1))
                    if len(visited_nodes) >= max_nodes_returned:
                        break

        sub_nodes = [self.nodes[nid] for nid in visited_nodes if nid in self.nodes]
        sub_edges: List[Dict[str, Any]] = []
        for u in visited_nodes:
            for v, edata in self.adj.get(u, {}).items():
                if v in visited_nodes:
                    sub_edges.append(edata)

        shared_devices = [
            {"device_id": dev, "accounts": sorted(list(accs)), "account_count": len(accs)}
            for dev, accs in self.device_to_accounts.items()
            if len(accs) > 1
        ]

        return {
            "center_id": center_id,
            "available_entities": sorted(
                [nid for nid, d in self.nodes.items() if d.get("node_type") in ("ACCOUNT", "DEVICE", "MERCHANT")],
                key=lambda x: float(self.nodes[x].get("risk_score", 0.0)),
                reverse=True,
            )[:50],
            "nodes": sub_nodes,
            "edges": sub_edges,
            "summary": {
                "node_count": len(sub_nodes),
                "edge_count": len(sub_edges),
                "total_graph_nodes": len(self.nodes),
                "shared_devices": shared_devices[:10],
                "suspicious_clusters": len(shared_devices),
                "engine_backend": "networkx+native" if NETWORKX_INSTALLED else "native_bounded_multidigraph",
            },
        }
