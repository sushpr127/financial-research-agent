import time

# Gemini 1.5 Pro pricing (per 1M tokens, as of 2026)
COST_PER_1M_INPUT_TOKENS  = 3.50   # USD
COST_PER_1M_OUTPUT_TOKENS = 10.50  # USD

# Gemini 1.5 Flash pricing
FLASH_COST_PER_1M_INPUT  = 0.075
FLASH_COST_PER_1M_OUTPUT = 0.30


class RunTracker:
    """
    Tracks token usage and estimated cost for one pipeline run.
    """
    def __init__(self, ticker: str):
        self.ticker     = ticker
        self.start_time = time.time()
        self.calls      = []

    def log(self, agent: str, model: str, input_tokens: int, output_tokens: int):
        if "flash" in model.lower():
            input_cost  = (input_tokens  / 1_000_000) * FLASH_COST_PER_1M_INPUT
            output_cost = (output_tokens / 1_000_000) * FLASH_COST_PER_1M_OUTPUT
        else:
            input_cost  = (input_tokens  / 1_000_000) * COST_PER_1M_INPUT_TOKENS
            output_cost = (output_tokens / 1_000_000) * COST_PER_1M_OUTPUT_TOKENS

        self.calls.append({
            "agent":         agent,
            "model":         model,
            "input_tokens":  input_tokens,
            "output_tokens": output_tokens,
            "cost_usd":      round(input_cost + output_cost, 6)
        })

    def summary(self) -> dict:
        elapsed       = round(time.time() - self.start_time, 2)
        total_input   = sum(c["input_tokens"]  for c in self.calls)
        total_output  = sum(c["output_tokens"] for c in self.calls)
        total_cost    = sum(c["cost_usd"]      for c in self.calls)

        return {
            "ticker":        self.ticker,
            "elapsed_sec":   elapsed,
            "total_input_tokens":  total_input,
            "total_output_tokens": total_output,
            "estimated_cost_usd":  round(total_cost, 6),
            "calls":         self.calls
        }

    def print_summary(self):
        s = self.summary()
        print(f"\n{'='*50}")
        print(f"💰 Cost & Token Summary for {s['ticker']}")
        print(f"{'='*50}")
        print(f"  Total time:     {s['elapsed_sec']}s")
        print(f"  Input tokens:   {s['total_input_tokens']:,}")
        print(f"  Output tokens:  {s['total_output_tokens']:,}")
        print(f"  Estimated cost: ${s['estimated_cost_usd']:.4f} USD")
        print(f"\n  Per-agent breakdown:")
        for call in s["calls"]:
            print(f"    {call['agent']:<20} {call['model']:<20} "
                  f"in={call['input_tokens']:>5} out={call['output_tokens']:>5} "
                  f"${call['cost_usd']:.6f}")