# 🗄️ Data Storage

### `Dealer`

| Поле | Тип |
|------|-----|
| `google_place_id` | str (unique) |
| `name`, `address`, `city` | str |
| `lat`, `lng` | float |
| `rating` | float \| null |
| `user_ratings_total` | int |
| `website`, `phone` | str \| null |
| `last_synced_at` | datetime (auto_now) |

### `SearchCache`

| Поле | Тип |
|------|-----|
| `query_key` | str (unique) |
| `results_json` | json |
| `created_at` | datetime |

### `User`

| Поле | Тип |
|------|-----|
| `email` | str (unique, USERNAME_FIELD) |
| `google_sub` | str \| null (unique) |
| `plan` | str (`free` / `premium`) |
| `daily_quota` | int (default 15) |
| `ai_daily_quota` | int (default 15) |
| `terms_accepted` | bool |

> ℹ️ Счётчики использования (`used_today`) вынесены в Redis: `quota:user:{pk}:{date}` и `quota:anon:{ip}:{date}`, TTL до следующей полуночи.

### `Favorite`

| Поле | Тип |
|------|-----|
| `user` | FK→User |
| `place_id` | str |
| `name`, `address`, `city` | str |
| `rating` | float \| null |
| `phone`, `website` | str |
| `lat`, `lng` | float \| null |
| `created_at` | datetime |

unique_together: `(user, place_id)`

### `PopularSearch`

| Поле | Тип |
|------|-----|
| `city` | str (unique) |
| `count` | int |
| `updated_at` | datetime (auto_now) |

### `UserSearchHistory`

| Поле | Тип |
|------|-----|
| `user` | FK→User |
| `city` | str |
| `searched_at` | datetime |