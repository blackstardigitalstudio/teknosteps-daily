# TeknoSteps — Daily (cloud)

Crea e pubblica ogni giorno i video + Short dei 3 canali YouTube (TeknoSteps,
Strange Light, Tekno Monkey) **senza PC acceso**, via GitHub Actions.

- Workflow: `.github/workflows/daily.yml` — parte alle **07:00 Italia** (cron `0 5 * * *` UTC) e si puo' lanciare a mano (Actions → Run workflow).
- Codice: gli stessi script della pipeline locale. Entrypoint `pubblica_giornaliero.py`.
- Asset (font, video pavimento, clip Kling, voci/jingle, ~74MB): scaricati a runtime da `teknosteps.com/assets/live/pipeline_assets.tar.gz` (non nel repo).
- Credenziali: NON nel repo. Stanno nei **GitHub Secrets** (base64) e vengono ricostruite a runtime:
  - `CLIENT_SECRET_B64`, `TOKEN_CH1_B64`, `TOKEN_CH2_B64`, `TOKEN_CH3_B64`.

## Rigenerare un token (se scade)
Sul PC: `python youtube_upload.py --auth-only --token token_ch2.json`, poi aggiorna il secret:
`base64 -w0 token_ch2.json | gh secret set TOKEN_CH2_B64 --body -`

Made in Italy.
