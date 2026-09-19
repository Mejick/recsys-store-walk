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
| 4c. Demo formula (hazard tables + history) | 0.3107 | 0.6125 | 0.5073 |
| CatBoost MultiClass | 0.3164 | 0.6224 | 0.5139 |
| CatBoost YetiRank (subsample) | 0.2577 | 0.5244 | 0.4484 |

### Срезы, hit@3 (val)

| Метод | k=1 (n=22,752) | k=2-3 (n=39,658) | k>=4 (n=66,829) | new users (<=4 prior orders) (n=35,119) | old users (>4 prior orders) (n=94,120) | target not in global top-3 (n=83,279) |
|---|---|---|---|---|---|---|
| 1. Global popularity | 0.5284 | 0.4970 | 0.4953 | 0.4934 | 0.5047 | 0.2266 |
| 2. Personal popularity | 0.6634 | 0.6251 | 0.5867 | 0.5760 | 0.6254 | 0.4666 |
| 3. Markov chain (order 1) | 0.5581 | 0.5161 | 0.5002 | 0.5063 | 0.5186 | 0.2583 |
| 4. Prototype heuristic | 0.4578 | 0.4606 | 0.4740 | 0.4540 | 0.4719 | 0.4848 |
| 4b. Heuristic with directed lift | 0.5525 | 0.5435 | 0.5226 | 0.5087 | 0.5439 | 0.4538 |
| 4c. Demo formula (hazard tables + history) | 0.6628 | 0.6242 | 0.5885 | 0.5821 | 0.6238 | 0.4485 |
| CatBoost MultiClass | 0.6757 | 0.6347 | 0.5969 | 0.5950 | 0.6326 | 0.4732 |
| CatBoost YetiRank (subsample) | 0.5737 | 0.5285 | 0.5051 | 0.5127 | 0.5287 | 0.2680 |

## test (130,158 примеров, 22,675 заказов)

| Метод | hit@1 | hit@3 | MRR |
|---|---|---|---|
| 1. Global popularity | 0.2135 | 0.5058 | 0.4181 |
| 2. Personal popularity | 0.3092 | 0.6203 | 0.5090 |
| 3. Markov chain (order 1) | 0.2489 | 0.5180 | 0.4420 |
| 4. Prototype heuristic | 0.1862 | 0.4719 | 0.3934 |
| 4b. Heuristic with directed lift | 0.2481 | 0.5421 | 0.4499 |
| 4c. Demo formula (hazard tables + history) | 0.3143 | 0.6188 | 0.5115 |
| CatBoost MultiClass | 0.3202 | 0.6274 | 0.5177 |
| CatBoost YetiRank (subsample) | 0.2606 | 0.5278 | 0.4506 |

### Срезы, hit@3 (test)

| Метод | k=1 (n=22,675) | k=2-3 (n=39,737) | k>=4 (n=67,746) | new users (<=4 prior orders) (n=25,572) | old users (>4 prior orders) (n=104,586) | target not in global top-3 (n=83,692) |
|---|---|---|---|---|---|---|
| 1. Global popularity | 0.5316 | 0.4993 | 0.5010 | 0.4925 | 0.5091 | 0.2314 |
| 2. Personal popularity | 0.6696 | 0.6313 | 0.5972 | 0.5937 | 0.6268 | 0.4759 |
| 3. Markov chain (order 1) | 0.5564 | 0.5165 | 0.5061 | 0.5068 | 0.5208 | 0.2621 |
| 4. Prototype heuristic | 0.4581 | 0.4662 | 0.4798 | 0.4664 | 0.4732 | 0.4920 |
| 4b. Heuristic with directed lift | 0.5544 | 0.5503 | 0.5332 | 0.5289 | 0.5453 | 0.4614 |
| 4c. Demo formula (hazard tables + history) | 0.6676 | 0.6303 | 0.5957 | 0.5966 | 0.6243 | 0.4532 |
| CatBoost MultiClass | 0.6777 | 0.6411 | 0.6026 | 0.6019 | 0.6337 | 0.4802 |
| CatBoost YetiRank (subsample) | 0.5744 | 0.5327 | 0.5093 | 0.5133 | 0.5313 | 0.2732 |

## Важность признаков (CatBoost, PredictionValuesChange, топ-20)

| Признак | Важность |
|---|---|
| heur[produce] | 6.3197 |
| basket[dairy eggs] | 5.9923 |
| basket[produce] | 4.3906 |
| heur[beverages] | 4.3669 |
| heur[dairy eggs] | 4.1558 |
| u_reorder_rate | 4.0059 |
| heur[snacks] | 3.1668 |
| heur[frozen] | 3.006 |
| heur[bakery] | 2.7612 |
| heur[deli] | 2.354 |
| last_aisle | 2.3137 |
| heur[meat seafood] | 2.2589 |
| share[produce] | 2.0687 |
| heur[pantry] | 2.0587 |
| share[dairy eggs] | 1.9815 |
| heur[babies] | 1.8769 |
| share[household] | 1.8234 |
| heur[breakfast] | 1.7446 |
| heur[canned goods] | 1.717 |
| share[pets] | 1.6286 |

Обозначения: `basket[d]` число позиций отдела d в корзине, `share[d]` доля прошлых заказов с отделом d, `markov[d]` P(следующий = d | последний отдел), `heur[d]` скор эвристики прототипа.

## Разобранные примеры (test)

**Пример 1.** Корзина после 2 позиций: produce×1, dairy eggs×1. Последний отдел: produce. История (7 заказов), чаще всего: produce (7/7), dairy eggs (7/7), babies (6/7). Реально следующий: **babies**.
- 1. Global popularity: snacks, pantry, frozen
- 2. Personal popularity: babies, pantry, frozen
- 3. Markov chain (order 1): snacks, pantry, frozen
- 4. Prototype heuristic: babies, pantry, bakery
- 4b. Heuristic with directed lift: babies, pantry, canned goods
- 4c. Demo formula (hazard tables + history): pantry, frozen, bakery
- CatBoost MultiClass: babies, bakery, frozen

**Пример 2.** Корзина после 2 позиций: produce×1, dairy eggs×1. Последний отдел: dairy eggs. История (3 заказов), чаще всего: produce (3/3), dairy eggs (3/3), beverages (3/3). Реально следующий: **beverages**.
- 1. Global popularity: snacks, pantry, frozen
- 2. Personal popularity: beverages, snacks, household
- 3. Markov chain (order 1): snacks, beverages, frozen
- 4. Prototype heuristic: beverages, snacks, personal care
- 4b. Heuristic with directed lift: beverages, snacks, bakery
- 4c. Demo formula (hazard tables + history): beverages, snacks, household
- CatBoost MultiClass: beverages, snacks, household

**Пример 3.** Корзина после 5 позиций: bakery×1, produce×2, dairy eggs×1, deli×1. Последний отдел: dairy eggs. История (14 заказов), чаще всего: produce (12/14), deli (11/14), dairy eggs (9/14). Реально следующий: **beverages**.
- 1. Global popularity: snacks, pantry, frozen
- 2. Personal popularity: beverages, meat seafood, frozen
- 3. Markov chain (order 1): snacks, beverages, frozen
- 4. Prototype heuristic: meat seafood, dry goods pasta, frozen
- 4b. Heuristic with directed lift: meat seafood, beverages, frozen
- 4c. Demo formula (hazard tables + history): beverages, frozen, meat seafood
- CatBoost MultiClass: beverages, meat seafood, frozen

**Пример 4.** Корзина после 6 позиций: produce×2, pets×1, personal care×1, dairy eggs×1, deli×1. Последний отдел: produce. История (20 заказов), чаще всего: beverages (16/20), dairy eggs (13/20), produce (12/20). Реально следующий: **beverages**.
- 1. Global popularity: snacks, pantry, frozen
- 2. Personal popularity: beverages, snacks, bakery
- 3. Markov chain (order 1): snacks, pantry, frozen
- 4. Prototype heuristic: beverages, snacks, bakery
- 4b. Heuristic with directed lift: beverages, snacks, bakery
- 4c. Demo formula (hazard tables + history): beverages, snacks, frozen
- CatBoost MultiClass: beverages, snacks, frozen

**Пример 5.** Корзина после 3 позиций: bakery×1, dry goods pasta×1, dairy eggs×1. Последний отдел: dairy eggs. История (88 заказов), чаще всего: produce (77/88), dairy eggs (72/88), bakery (39/88). Реально следующий: **snacks**.
- 1. Global popularity: snacks, produce, pantry
- 2. Personal popularity: produce, pantry, snacks
- 3. Markov chain (order 1): produce, snacks, beverages
- 4. Prototype heuristic: pantry, frozen, produce
- 4b. Heuristic with directed lift: produce, frozen, pantry
- 4c. Demo formula (hazard tables + history): produce, snacks, pantry
- CatBoost MultiClass: produce, frozen, pantry
