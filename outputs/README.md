# Outputs

One folder per simulation run, named the way the run is named:
`<Partner>/<weather>/<Scenario>`. Each holds numbered versions recording where
the result files live in S3 and exactly which inputs and code produced them.

The result files themselves are not stored in git — there are about 11 GB of them.
Download them with `globi-data outputs download <experiment>`.

See [STATUS.md](STATUS.md) for which results are up to date.

| Country | Experiment | Version | Run | Date | Results | Built from input |
|---|---|---|---|---|---|---|
| BR | [Sao_Paulo_Bela_Vista/ftmy/noAC](runs/Sao_Paulo_Bela_Vista/ftmy/noAC/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| BR | [Sao_Paulo_Bela_Vista/ftmy/withAC](runs/Sao_Paulo_Bela_Vista/ftmy/withAC/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| BR | [Sao_Paulo_Bela_Vista/tmy/noAC](runs/Sao_Paulo_Bela_Vista/tmy/noAC/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| BR | [Sao_Paulo_Bela_Vista/tmy/withAC](runs/Sao_Paulo_Bela_Vista/tmy/withAC/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| GB | [Manchester/ftmy/DSR](runs/Manchester/ftmy/DSR/) | `v001` | v1.0.0 | 2026-06-19 | 5 | `v001` |
| GB | [Manchester/ftmy/No_DSR](runs/Manchester/ftmy/No_DSR/) | `v001` | v1.0.0 | 2026-06-18 | 5 | `v001` |
| GB | [Manchester/tmy/DSR](runs/Manchester/tmy/DSR/) | `v001` | v1.0.0 | 2026-06-19 | 5 | `v001` |
| GB | [Manchester/tmy/No_DSR](runs/Manchester/tmy/No_DSR/) | `v001` | v1.0.0 | 2026-06-15 | 5 | `v001` |
| IN | [Ahmedabad/ftmy/BAU](runs/Ahmedabad/ftmy/BAU/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| IN | [Ahmedabad/ftmy/CC](runs/Ahmedabad/ftmy/CC/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| IN | [Ahmedabad/tmy/BAU](runs/Ahmedabad/tmy/BAU/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| IN | [Ahmedabad/tmy/CC](runs/Ahmedabad/tmy/CC/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| KE | [Nairobi/ftmy/noAC](runs/Nairobi/ftmy/noAC/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| KE | [Nairobi/ftmy/withAC](runs/Nairobi/ftmy/withAC/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| KE | [Nairobi/tmy/noAC](runs/Nairobi/tmy/noAC/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| KE | [Nairobi/tmy/withAC](runs/Nairobi/tmy/withAC/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| PT | [Lisbon/ftmy/Baseline](runs/Lisbon/ftmy/Baseline/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| PT | [Lisbon/ftmy/Retrofit](runs/Lisbon/ftmy/Retrofit/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| PT | [Lisbon/tmy/Baseline](runs/Lisbon/tmy/Baseline/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| PT | [Lisbon/tmy/Retrofit](runs/Lisbon/tmy/Retrofit/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| SG | [Singapore/ftmy/Baseline](runs/Singapore/ftmy/Baseline/) | `v001` | v1.0.0 | 2026-06-18 | 5 | `v001` |
| SG | [Singapore/ftmy/Retrofit](runs/Singapore/ftmy/Retrofit/) | `v001` | v1.0.0 | 2026-06-19 | 5 | `v001` |
| SG | [Singapore/tmy/Baseline](runs/Singapore/tmy/Baseline/) | `v001` | v1.0.0 | 2026-06-18 | 5 | `v001` |
| SG | [Singapore/tmy/Retrofit](runs/Singapore/tmy/Retrofit/) | `v001` | v1.0.0 | 2026-06-19 | 5 | `v001` |
| ? | [Trondheim/ftmy/HighEfficiency](runs/Trondheim/ftmy/HighEfficiency/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| ? | [Trondheim/ftmy/LowEfficiency](runs/Trondheim/ftmy/LowEfficiency/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| ? | [Trondheim/tmy/HighEfficiency](runs/Trondheim/tmy/HighEfficiency/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
| ? | [Trondheim/tmy/LowEfficiency](runs/Trondheim/tmy/LowEfficiency/) | `v001` | v1.0.0 | 2026-06-08 | 5 | `v001` |
