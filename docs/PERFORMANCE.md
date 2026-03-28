# ApexOdds Pro — Performance Guide

## Cached Functions
| Function | Decorator | TTL | Notes |
|---|---|---|---|
| load_latest_odds | @st.cache_data | 300s | Filtered by sport_key tuple |
| load_upcoming_matches | @st.cache_data | 300s | — |
| compute_summary_stats | @st.cache_data | 300s | KPI bar |
| compute_best_edge_map | @st.cache_data | 300s | PRO EDGE badges |
| get_db | @st.cache_resource | forever | Singleton DBManager |
| get_analyzer | @st.cache_resource | forever | Singleton OddsAnalyzer |

## Profiling with Browser DevTools
1. Open Chrome DevTools → Performance tab
2. Click Record
3. Interact with the dashboard (switch sections, refresh data)
4. Click Stop
5. Look for long tasks (red bars) in the Main thread
6. Correlate with Streamlit's WebSocket frames in the Network tab

## Known Slow Paths
- compute_summary_stats() on large datasets: use sport_key filter
- Plotly charts with >500 data points: pre-aggregate in Python
- render_match_card() called in a loop: batch into one HTML string
