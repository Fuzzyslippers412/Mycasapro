#!/bin/bash
# Quick BTC Oracle V2 runner
# Usage: ./oracle.sh <target_price> <time_seconds> <up_odds> <down_odds>
# Example: ./oracle.sh 78500 300 0.45 0.55

cd "$(dirname "$0")"

if [ $# -lt 4 ]; then
    echo "Usage: ./oracle.sh <target_price> <time_seconds> <up_odds> <down_odds>"
    echo "Example: ./oracle.sh 78500 300 0.45 0.55"
    echo ""
    echo "Quick scan (Binance only):"
    python3 -c "from btc_oracle_v2 import get_binance_data; import json; d=get_binance_data(); print(f'BTC: \${d[\"current_price\"]:,.2f} | Taker: {d[\"taker_ratio\"]:.2f} | Mom3m: {d[\"delta_p3\"]:+.3f}%')"
    exit 0
fi

python3 -c "
from btc_oracle_v2 import run_oracle
run_oracle($1, $2, $3, $4)
"
