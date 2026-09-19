# Метрики: следующий отдел, которого ещё нет в корзине

Топ-3 популярных таргета (исключаются в срезе «не из топ-3»): dairy eggs, snacks, produce.
Все методы ранжируют только отделы, которых ещё нет в корзине. Ничьи в счёте засчитываются против метода.

## val (129,239 примеров, 22,752 заказов)

| Метод | hit@1 | hit@3 | MRR |
|---|---|---|---|
| 1. Global popularity | 0.2120 | 0.5016 | 0.4159 |
| 2. Personal popularity | 0.3049 | 0.6120 | 0.5041 |
| 3. Markov chain (order 1) | 0.2465 | 0.5153 | 0.4399 |
| 4. Prototype heuristic | 0.1858 | 0.4670 | 0.3909 |
| 4b. Heuristic with directed lift | 0.2446 | 0.5343 | 0.4452 |
| CatBoost MultiClass | 0.3137 | 0.6207 | 0.5118 |
| CatBoost YetiRank (subsample) | 0.2568 | 0.5234 | 0.4476 |

### Срезы, hit@3 (val)

| Метод | k=1 (n=22,752) | k=2-3 (n=39,658) | k>=4 (n=66,829) | new users (<=4 prior orders) (n=35,119) | old users (>4 prior orders) (n=94,120) | target not in global top-3 (n=83,279) |
|---|---|---|---|---|---|---|
| 1. Global popularity | 0.5284 | 0.4970 | 0.4953 | 0.4934 | 0.5047 | 0.2266 |
| 2. Personal popularity | 0.6634 | 0.6251 | 0.5867 | 0.5760 | 0.6254 | 0.4666 |
| 3. Markov chain (order 1) | 0.5581 | 0.5161 | 0.5002 | 0.5063 | 0.5186 | 0.2583 |
| 4. Prototype heuristic | 0.4578 | 0.4606 | 0.4740 | 0.4540 | 0.4719 | 0.4848 |
| 4b. Heuristic with directed lift | 0.5525 | 0.5435 | 0.5226 | 0.5087 | 0.5439 | 0.4538 |
| CatBoost MultiClass | 0.6724 | 0.6320 | 0.5963 | 0.5896 | 0.6323 | 0.4713 |
| CatBoost YetiRank (subsample) | 0.5730 | 0.5279 | 0.5037 | 0.5107 | 0.5281 | 0.2667 |

## test (130,158 примеров, 22,675 заказов)

| Метод | hit@1 | hit@3 | MRR |
|---|---|---|---|
| 1. Global popularity | 0.2135 | 0.5058 | 0.4181 |
| 2. Personal popularity | 0.3092 | 0.6203 | 0.5090 |
| 3. Markov chain (order 1) | 0.2489 | 0.5180 | 0.4420 |
| 4. Prototype heuristic | 0.1862 | 0.4719 | 0.3934 |
| 4b. Heuristic with directed lift | 0.2481 | 0.5421 | 0.4499 |
| CatBoost MultiClass | 0.3166 | 0.6253 | 0.5149 |
| CatBoost YetiRank (subsample) | 0.2592 | 0.5261 | 0.4496 |

### Срезы, hit@3 (test)

| Метод | k=1 (n=22,675) | k=2-3 (n=39,737) | k>=4 (n=67,746) | new users (<=4 prior orders) (n=25,572) | old users (>4 prior orders) (n=104,586) | target not in global top-3 (n=83,692) |
|---|---|---|---|---|---|---|
| 1. Global popularity | 0.5316 | 0.4993 | 0.5010 | 0.4925 | 0.5091 | 0.2314 |
| 2. Personal popularity | 0.6696 | 0.6313 | 0.5972 | 0.5937 | 0.6268 | 0.4759 |
| 3. Markov chain (order 1) | 0.5564 | 0.5165 | 0.5061 | 0.5068 | 0.5208 | 0.2621 |
| 4. Prototype heuristic | 0.4581 | 0.4662 | 0.4798 | 0.4664 | 0.4732 | 0.4920 |
| 4b. Heuristic with directed lift | 0.5544 | 0.5503 | 0.5332 | 0.5289 | 0.5453 | 0.4614 |
| CatBoost MultiClass | 0.6767 | 0.6368 | 0.6013 | 0.5986 | 0.6318 | 0.4784 |
| CatBoost YetiRank (subsample) | 0.5742 | 0.5315 | 0.5068 | 0.5111 | 0.5297 | 0.2710 |

## Важность признаков (CatBoost, PredictionValuesChange, топ-20)

| Признак | Важность |
|---|---|
| basket[dairy eggs] | 5.178 |
| heur[dairy eggs] | 4.9167 |
| heur[beverages] | 4.9066 |
| heur[produce] | 4.7884 |
| basket[produce] | 4.3483 |
| u_reorder_rate | 3.8866 |
| heur[snacks] | 3.6593 |
| heur[frozen] | 3.1637 |
| heur[bakery] | 2.9388 |
| heur[deli] | 2.3049 |
| heur[meat seafood] | 2.2784 |
| heur[pantry] | 2.0191 |
| heur[canned goods] | 1.9261 |
| last_aisle | 1.8966 |
| share[dairy eggs] | 1.8965 |
| heur[dry goods pasta] | 1.8216 |
| heur[babies] | 1.7943 |
| heur[breakfast] | 1.7849 |
| heur[household] | 1.7145 |
| share[household] | 1.6954 |

Обозначения: `basket[d]` число позиций отдела d в корзине, `share[d]` доля прошлых заказов с отделом d, `markov[d]` P(следующий = d | последний отдел), `heur[d]` скор эвристики прототипа.

## Разобранные примеры (test)

**Пример 1.** Корзина после 5 позиций: produce×1, beverages×2, pantry×1, dairy eggs×1. Последний отдел: pantry. История (10 заказов), чаще всего: beverages (10/10), dairy eggs (9/10), deli (5/10). Реально следующий: **deli**.
- 1. Global popularity: snacks, frozen, bakery
- 2. Personal popularity: deli, dry goods pasta, snacks
- 3. Markov chain (order 1): snacks, frozen, canned goods
- 4. Prototype heuristic: deli, dry goods pasta, international
- 4b. Heuristic with directed lift: dry goods pasta, deli, international
- CatBoost MultiClass: deli, dry goods pasta, frozen

**Пример 2.** Корзина после 5 позиций: produce×4, dairy eggs×1. Последний отдел: produce. История (42 заказов), чаще всего: produce (42/42), dairy eggs (42/42), canned goods (35/42). Реально следующий: **deli**.
- 1. Global popularity: snacks, pantry, frozen
- 2. Personal popularity: canned goods, deli, breakfast
- 3. Markov chain (order 1): snacks, pantry, frozen
- 4. Prototype heuristic: canned goods, deli, pantry
- 4b. Heuristic with directed lift: canned goods, deli, pantry
- CatBoost MultiClass: deli, canned goods, breakfast

**Пример 3.** Корзина после 6 позиций: produce×3, dry goods pasta×2, dairy eggs×1. Последний отдел: dairy eggs. История (30 заказов), чаще всего: produce (28/30), dairy eggs (26/30), beverages (24/30). Реально следующий: **beverages**.
- 1. Global popularity: snacks, pantry, frozen
- 2. Personal popularity: beverages, canned goods, pantry
- 3. Markov chain (order 1): snacks, beverages, frozen
- 4. Prototype heuristic: canned goods, meat seafood, pantry
- 4b. Heuristic with directed lift: canned goods, bakery, meat seafood
- CatBoost MultiClass: beverages, pantry, canned goods

**Пример 4.** Корзина после 2 позиций: produce×2. Последний отдел: produce. История (6 заказов), чаще всего: produce (6/6), bakery (4/6). Реально следующий: **bakery**.
- 1. Global popularity: dairy eggs, snacks, pantry
- 2. Personal popularity: bakery, dairy eggs, snacks
- 3. Markov chain (order 1): dairy eggs, snacks, pantry
- 4. Prototype heuristic: bakery, bulk, canned goods
- 4b. Heuristic with directed lift: bakery, bulk, canned goods
- CatBoost MultiClass: bakery, dairy eggs, snacks

**Пример 5.** Корзина после 4 позиций: produce×3, dairy eggs×1. Последний отдел: dairy eggs. История (10 заказов), чаще всего: produce (10/10), dairy eggs (7/10), meat seafood (5/10). Реально следующий: **snacks**.
- 1. Global popularity: snacks, pantry, frozen
- 2. Personal popularity: meat seafood, snacks, pantry
- 3. Markov chain (order 1): snacks, beverages, frozen
- 4. Prototype heuristic: meat seafood, dry goods pasta, pantry
- 4b. Heuristic with directed lift: meat seafood, bakery, snacks
- CatBoost MultiClass: meat seafood, bakery, pantry
