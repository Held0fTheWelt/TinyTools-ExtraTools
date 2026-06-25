# Metrify

Metrify tracks AI usage, token spend, cost drivers, and cost-versus-utility signals for the `fy` suite family.

## What it does

- records token and cost events per run, suite, model, and technique
- computes rolling summaries for the last run, last 10 runs, today, and all time
- highlights biggest cost drivers by suite, model, and technique
- suggests optimization opportunities such as cached-input use, smaller-model candidates, and output-token pressure
- emits observability-friendly reports for `observifyfy`
- emits AI-friendly context packs and `llms.txt`

## Commands

```bash
metrify record --suite contractify --run-id run-001 --model gpt-5.4 --input-tokens 1000 --output-tokens 500
metrify ingest --source usage.jsonl
metrify report
metrify ai-pack
metrify full
```

## Limits

Metrify cannot magically observe every AI call on its own. It needs either:
- direct instrumentation from the calling suite,
- imported usage logs, or
- explicit `record` calls.

That keeps the metric trail honest.
