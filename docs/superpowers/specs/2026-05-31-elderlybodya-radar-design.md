# ElderlyBodya Radar — Design Spec

Дата: 2026-05-31
Статус: на ревью пользователя

## 1. Цель

Ежедневный «контент-радар» для Telegram-канала **@elderlybodya**. Раз в сутки собирает свежие сигналы из нескольких источников, фильтрует шум, ранжирует и присылает владельцу в личку **готовые черновики постов + ссылки на источники**. Владелец правит и публикует сам. Полностью бесплатно ($0).

**Не** автопостинг. Человек — финальный фильтр (снимает риск непроверённых тренировочных/мед-советов).

## 2. Домен и голос

Канал = **силовые / пауэрлифтинг / бодибилдинг** (НЕ гериатрический фитнес — «elderly» в названии иронично). Темы: жим лёжа, присед, становая, тренировочные раскладки и проценты от 1ПМ, гипертрофия, набор массы, БЖУ/питание, техника, добавки (креатин и т.п.).

Аудитория: мужчины-лифтеры, средний+ стаж.

**Голос** (снят с `bench_presses_article.docx`):
- прямой, экспертный, без воды;
- конкретика — кг, проценты, подходы/повторы;
- обращение на «вы»;
- лёгкая ирония (напр. над «лайками в тиктоке/инсте»);
- уместен сленг зала;
- форматы: и короткие посты, и длинные гайды.

> ⚠️ В выгрузке Telegram **отсутствует `messages.html`** — фактических коротких постов нет, голос снят с одной статьи. Перед финальной настройкой writer нужны 3-5 реальных постов (доэкспорт с messages.html или вставка текстом). До этого writer работает на style-guide выше; шлифуется после первого прогона.

## 3. Зафиксированные решения

| Решение | Выбор |
|---|---|
| Выход | Готовые черновики + ссылки → владельцу в ЛС; публикует вручную |
| Деплой | GitHub Actions cron (облако, $0) |
| LLM | Google Gemini Flash (free tier) |
| Источники v1 | PubMed + Europe PMC, RSS, Reddit, YouTube Data API |
| Доставка | Telegram-бот в личку, раз в день |
| Состояние/дедуп | GitHub Actions cache (SQLite-файл) |
| Расположение | `D:\elderlybodya-radar`, git, public-репо GitHub |

## 4. Архитектура

Модульный пайплайн, один процесс, без очередей/агентов/кластера.

```
elderlybodya-radar/
  radar/
    sources/        # адаптеры: pubmed.py europepmc.py rss.py reddit.py youtube.py
    store.py        # SQLite: items + dedup по (source, source_id)
    filter.py       # keyword-фильтр + dedup, режет шум ДО LLM
    llm.py          # Gemini-клиент: rank(top-N) + draft(post)
    writer.py       # сборка промптов: style-guide + примеры
    delivery.py     # Telegram bot → chat_id владельца
    digest.py       # форматирование дайджеста, сплит >4096
    config.py       # загрузка config.yaml + env-секретов
    main.py         # пайплайн, точка входа (python -m radar.main)
  config.yaml
  requirements.txt
  tests/
  docs/superpowers/specs/
  .github/workflows/daily.yml
```

**Поток данных (раз в день):**

```
cron → main → fetch все источники (async, parallel)
            → normalize → Item
            → store.dedup (пропустить виденное по source_id)
            → filter (keywords) → кандидаты
            → llm.rank: 1 батч-вызов, выбрать top-N (default 5)
            → llm.draft: черновик на каждый выбранный
            → digest.format → delivery.telegram (владельцу)
            → store.mark_seen → save cache
```

**Единый формат записи:**
```python
Item = {
  source: str,        # "pubmed" | "europepmc" | "rss" | "reddit" | "youtube"
  source_id: str,     # уникальный id в источнике (PMID, url, reddit id, video id)
  title: str,
  url: str,
  text: str,          # аннотация / сниппет / описание
  published_at: datetime,
}
```

## 5. Компоненты (границы)

Каждый — одна задача, тестируется изолированно.

- **sources/\*** — один адаптер на источник. Вход: config (запросы/каналы) + http. Выход: `list[Item]`. Зависимости: внешние API. Изолированы за общим интерфейсом `fetch(cfg) -> list[Item]`.
- **store.py** — SQLite. Таблица `items` + индекс по `(source, source_id)`. Методы: `is_seen()`, `add()`, `mark_seen()`, `prune(older_than)`. Файл персистится через Actions cache.
- **filter.py** — отбор по keyword-спискам (RU+EN) + дедуп против стора. Вход: `list[Item]`. Выход: отфильтрованные кандидаты. Без сети/LLM.
- **llm.py** — обёртка Gemini. `rank(candidates) -> list[selected_id, reason]` (1 вызов). `draft(item, style) -> {text, alt_titles}`. Ретрай с backoff на 429.
- **writer.py** — строит промпты: системный style-guide + примеры постов + данные item. Не ходит в сеть напрямую (через llm.py).
- **digest.py** — формат дайджеста: шапка (дата, кол-во кандидатов по источникам, ошибки) + по сообщению на черновик (удобно копировать). Сплит >4096 символов.
- **delivery.py** — Telegram Bot API `sendMessage` на `TELEGRAM_CHAT_ID`. Без внешних SDK (requests к api.telegram.org).
- **main.py** — оркестрация потока, обработка ошибок, выходной код.

## 6. Источники v1 (конкретика; значения в config.yaml)

- **PubMed (NCBI E-utilities)** + **Europe PMC** REST — бесплатно, без ключа (PubMed желателен api_key для лимита). Запросы: `resistance training`, `muscle hypertrophy`, `bench press`, `progressive overload`, `muscle protein synthesis`, `creatine`, `periodization`. Фильтр по дате (последние N дней).
- **RSS** (feedparser) — ленты силовых блогов/конкурентов. Список URL — заполняет владелец.
- **Reddit** (бесплатный API, OAuth script-app) — сабреддиты: `powerlifting`, `weightroom`, `naturalbodybuilding`, `bodybuilding`, `Fitness`. Листинг top/day, лимит ~25.
- **YouTube Data API v3** (бесплатная квота, ключ Google Cloud) — каналы тренеров (id заполняет владелец), новые видео: заголовок + описание.

**Keywords (config, RU+EN):** жим лёжа, присед, становая, гипертрофия, масса, БЖУ, креатин, профицит, программа, периодизация, объём, RPE, техника, протеин; hypertrophy, resistance training, strength, bench press, 1RM, progressive overload, muscle protein synthesis, periodization, volume.

## 7. LLM-слой (Gemini free)

- **rank** — один вызов на всех кандидатов: оценить релевантность теме канала + новизну, вернуть top-N id + 1 строка обоснования.
- **draft** — на каждый выбранный: готовый TG-пост в голосе канала (RU) — цепляющий заход, 2-4 коротких абзаца, практический вывод, в конце ссылка-источник; + 2-3 варианта заголовка. Где уместно (тренировочные/мед-утверждения) — мягкая оговорка «не мед-совет».
- **Бюджет free-tier:** dedup + keyword-фильтр срезают ~90% до LLM. Итого ~6-10 вызовов/день. Лимит Gemini Flash free ~1500/день → запас 100×.

## 8. Доставка

Telegram Bot API. Бот шлёт владельцу: сначала summary-сообщение (дата, что собрано, ошибки источников), затем по сообщению на черновик. Длинные режутся по 4096. Токен и `chat_id` — секреты.

## 9. Состояние / дедуп

SQLite-файл `state/seen.sqlite`. Персист между прогонами — **GitHub Actions cache** (ключ с run_id + `restore-keys: state-` для отката к последнему). Ежедневный прогон держит кеш «тёплым». Риск: пауза >7 дней → возможна эвикция → 1 день возможных повторов (приемлемо, дедуп best-effort). Прун записей старше 60 дней.

## 10. Отказоустойчивость

- Источник упал → остальные продолжают; в дайджесте «⚠ Reddit недоступен».
- Gemini-квота/ошибка → fallback: шлю сырые отфильтрованные кандидаты (заголовки+ссылки), сигнал не теряется.
- Telegram send fail → ненулевой выход → workflow красный → GitHub шлёт письмо владельцу.
- Ретрай с backoff на сетевые 429/5xx.

## 11. Конфиг и секреты

- `config.yaml` — timezone (Europe/Moscow), run_hour (6), drafts_per_day (5), language (ru), keywords, список источников/сабреддитов/RSS/YouTube-каналов.
- Секреты в **GitHub Actions Secrets** (заводятся на деплое): `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`, `YOUTUBE_API_KEY`. Опц. `PUBMED_API_KEY`.
- `.github/workflows/daily.yml` — `schedule: cron '0 3 * * *'` (03:00 UTC = 06:00 МСК) + `workflow_dispatch`; шаги: checkout → setup-python 3.12 → restore cache → pip install → `python -m radar.main` (env=secrets) → save cache.

## 12. Тестирование

pytest, TDD. Юнит: каждый адаптер парсит фикстуру (сохранённый JSON/XML) → корректный `Item`; filter; dedup; digest-форматтер; сплиттер сообщений. Сеть и LLM мокаются. CLI `--dry-run` — печатает дайджест в stdout, без отправки и (опц.) без LLM.

## 13. Не-цели (v2+)

- TikTok-скрейпинг (нет API, хрупко).
- Чтение чужих Telegram-каналов/чатов (нужен user-client Telethon, риск бана).
- Автопостинг в канал.
- Prometheus/Grafana, RabbitMQ, Kubernetes, multi-agent-оркестратор (оверкилл для дневного крона).

## 14. Открытые вопросы (к ревью)

1. **Подтвердить домен:** силовые/лифтинг (не пожилые) — верно?
2. **Голос:** доэкспорт `messages.html` или 3-5 постов текстом (иначе writer на style-guide, шлифуем после 1-го прогона).
3. **Источники-конкретика:** какие RSS-ленты и какие YouTube-каналы (id) добавить в config.
4. **Репо:** имя public-репо на GitHub + есть ли `gh`/аккаунт.
5. **Время/объём:** 06:00 МСК, 5 черновиков/день — ок?
