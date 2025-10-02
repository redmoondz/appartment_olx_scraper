# ⚠️ Проблема: Данные не собираются

## 🔍 Быстрая диагностика (1 минута)

### Шаг 1: Проверьте лог последнего запуска
```bash
tail -50 logs/olx_scraper_*.log | grep "Enrich data"
```

**Ожидаемый результат:**
```
Enrich data: True, Fetch phones: False
```

❌ **Если видите `Enrich data: False`** - это причина проблемы!

### Шаг 2: Проверьте результаты
```bash
python main.py stats
```

**Должно быть:**
- ✅ Все поля заполнены (100%)

❌ **Если много пустых полей** - данные собраны без обогащения

---

## ✅ Решение

### Вариант 1: Пересобрать данные (РЕКОМЕНДУЕТСЯ)

```bash
# 1. Бэкап старого кеша
mv cache/apartments_cache.csv cache/apartments_cache_backup.csv

# 2. Собрать заново С ОБОГАЩЕНИЕМ (без --no-details!)
python main.py scrape -p 10

# 3. Проверить результаты
python main.py stats
```

### Вариант 2: Добавить только новые с обогащением

```bash
# Собрать только новые квартиры С обогащением
python main.py scrape -n

# Проверить результаты
python main.py stats
```

---

## 🚫 ЧАСТЫЕ ОШИБКИ

### ❌ ОШИБКА #1: Использование `--no-details`
```bash
# НЕ ДЕЛАТЬ ТАК:
python main.py scrape --no-details  # ← Неполные данные!
```

**Последствие:** 
- ❌ Нет описания
- ❌ Нет тегов
- ❌ Нет этажа
- ❌ Нет фото
- ❌ Нет параметров

### ❌ ОШИБКА #2: Не проверять логи
```bash
# ВСЕГДА проверяйте, что в логах:
grep "Enrich data: True" logs/olx_scraper_*.log
```

### ❌ ОШИБКА #3: Не использовать `-n` для обновлений
```bash
# ПРАВИЛЬНО (обновление без пересбора всего):
python main.py scrape -n

# НЕПРАВИЛЬНО (пересбор всего каждый раз):
mv cache/apartments_cache.csv cache/old.csv
python main.py scrape -p 50
```

---

## ✅ ПРАВИЛЬНЫЕ КОМАНДЫ

### Первый сбор (полная база):
```bash
python main.py scrape -p 20
```

### Регулярные обновления (только новые):
```bash
python main.py scrape -n
```

### Быстрый режим (агрессивность 8):
```bash
python main.py scrape -p 10 -a 8
```

### С телефонами (медленнее):
```bash
python main.py scrape -p 5 --fetch-phones
```

---

## 🔧 Тестирование парсинга вручную

Если сомневаетесь, что код работает:

```bash
python3 << 'EOF'
import asyncio
from bs4 import BeautifulSoup
import aiohttp

async def test():
    url = "https://www.olx.ua/d/uk/obyavlenie/ВСТАВЬТЕ_URL_ПРОБЛЕМНОЙ_СТРАНИЦЫ"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, 'lxml')
            
            # Проверка описания
            desc = soup.find('div', class_='css-19duwlz')
            print(f"✅ Описание найдено: {desc is not None}")
            if desc:
                print(f"   Текст: {desc.get_text(strip=True)[:100]}...")
            
            # Проверка параметров
            params_container = soup.find('div', {'data-testid': 'ad-parameters-container', 'class': 'css-6zsv65'})
            print(f"✅ Контейнер параметров: {params_container is not None}")
            if params_container:
                params = params_container.find_all('p', class_='css-13x8d99')
                print(f"   Найдено тегов: {len(params)}")
                for p in params[:3]:
                    print(f"   - {p.get_text(strip=True)}")

asyncio.run(test())
EOF
```

**Ожидаемый результат:**
```
✅ Описание найдено: True
   Текст: Сдам однокомнатную квартиру...
✅ Контейнер параметров: True
   Найдено тегов: 9
   - Бізнес
   - Поверх: 2
   - Поверховість: 3
```

---

## 📊 Проверка качества данных

### Скрипт проверки:
```bash
python3 << 'EOF'
import pandas as pd

df = pd.read_csv('cache/apartments_cache.csv')

print(f"Всего записей: {len(df)}\n")

fields = ['description', 'tags', 'floor', 'photos']
for field in fields:
    if field in df.columns:
        filled = df[field].notna().sum()
        percent = filled / len(df) * 100
        status = "✅" if percent > 90 else "⚠️" if percent > 50 else "❌"
        print(f"{status} {field:15} {filled}/{len(df)} ({percent:.1f}%)")
EOF
```

**Ожидаемый результат (100% обогащение):**
```
Всего записей: 149

✅ description      149/149 (100.0%)
✅ tags             149/149 (100.0%)
✅ floor            149/149 (100.0%)
✅ photos           149/149 (100.0%)
```

---

## 🆘 Если ничего не помогает

### 1. Проверьте селекторы (могут измениться на сайте):

**Текущие селекторы (октябрь 2025):**
- Описание: `div.css-19duwlz`
- Контейнер параметров: `div[data-testid="ad-parameters-container"].css-6zsv65`
- Теги: `p.css-13x8d99`
- Просмотры: `span.css-16uueru`

### 2. Проверьте доступность OLX:
```bash
curl -I https://www.olx.ua/
```

### 3. Проверьте зависимости:
```bash
pip install -r requirements.txt --upgrade
```

### 4. Очистите кеш и пересоберите:
```bash
python main.py clear-cache
python main.py scrape -p 5
```

---

## 📝 Контрольный список

Перед обращением за помощью, проверьте:

- [ ] Лог показывает `Enrich data: True`
- [ ] НЕ используется флаг `--no-details`
- [ ] Интернет работает нормально
- [ ] OLX.ua доступен
- [ ] Зависимости установлены
- [ ] Тестовый скрипт парсинга работает
- [ ] Статистика показывает заполненные поля

---

**Если всё это проверено и проблема остаётся - возможно изменилась структура HTML на сайте OLX.**

В этом случае нужно обновить селекторы в файле `src/core/olx_api.py`.
