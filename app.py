import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re

st.set_page_config(page_title="RUZ Planner", layout="wide")
st.title("📅 RUZ Planner")

# ========================= СЛОВАРИ =========================
GROUP_MAP = {
    "3733801/50001": "41846",
    "3733801/50002": "41847",
    "3733801/50003": "41848",
    "3733801/50004": "41849",
    "3743809/40101": "42004",
}

TEACHER_MAP = {
    "Зайцев Андрей Александрович": "19997",
    "Благова Ирина Юрьевна": "23640",
    "Степанова Ксения Сергеевна": "20342",
}

# ========================= ПАРСЕР МЕСТА =========================
def parse_place(place_element):
    if not place_element:
        return "Не указано"
    link = place_element.find('a', class_='lesson__link')
    if not link:
        return "Не указано"
    text = link.get_text(strip=True)
    text = re.sub(r'(\d)(ауд\.)', r'\1 \2', text)
    parts = [p.strip() for p in text.split(',') if p.strip()]
    return ', '.join(dict.fromkeys(parts))

# ========================= ПАРСЕР ГРУППЫ (исправленный) =========================
def parse_group_schedule(group_human: str, start_date: datetime, end_date: datetime):
    if group_human not in GROUP_MAP:
        st.error(f"Группа {group_human} не найдена.")
        return pd.DataFrame()

    group_id = GROUP_MAP[group_human]
    all_lessons = []
    
    # Первый понедельник >= start_date
    days_ahead = 0 - start_date.weekday()
    if days_ahead < 0:
        days_ahead += 7
    current = start_date + timedelta(days=days_ahead)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 1

    while current <= end_date:
        week_count += 1
        url = f"https://ruz.spbstu.ru/faculty/100/groups/{group_id}?date={current.strftime('%Y-%m-%d')}"
        status_text.text(f"Обработка недели {week_count} из {total_weeks} (дата {current.strftime('%d.%m.%Y')})")

        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for day in soup.find_all('li', class_='schedule__day'):
                    date_elem = day.find('div', class_='schedule__date')
                    if not date_elem:
                        continue
                    date_text = date_elem.text.strip()
                    # Фильтр по дате
                    try:
                        lesson_date = datetime.strptime(date_text, "%d.%m.%Y")
                        if lesson_date < start_date or lesson_date > end_date:
                            continue
                    except:
                        pass

                    for lesson in day.find_all('li', class_='lesson'):
                        subject = ""
                        subject_elem = lesson.find('div', class_='lesson__subject')
                        if subject_elem:
                            spans = subject_elem.find_all('span')
                            if spans and len(spans) > 2:
                                subject = spans[-1].text.strip()

                        lesson_type = lesson.find('div', class_='lesson__type')
                        lesson_type = lesson_type.text.strip() if lesson_type else ""

                        teachers = []
                        teachers_elem = lesson.find('div', class_='lesson__teachers')
                        if teachers_elem:
                            for a in teachers_elem.find_all('a'):
                                name = a.text.strip()
                                if name and len(name) > 3:
                                    teachers.append(name)

                        time_str = lesson.find('span', class_='lesson__time')
                        time_str = time_str.text.strip() if time_str else ""

                        place = parse_place(lesson.find('div', class_='lesson__places'))

                        if subject and teachers:
                            all_lessons.append({
                                "Дата": date_text,
                                "Время": time_str,
                                "Дисциплина": subject,
                                "Тип занятия": lesson_type,
                                "Преподаватель": ", ".join(teachers),
                                "Место": place,
                                "Группа": group_human
                            })

            progress_bar.progress(min(week_count / total_weeks, 1.0))
            time.sleep(12)
        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {e}")

        current += timedelta(weeks=1)

    status_text.empty()
    return pd.DataFrame(all_lessons)

# ========================= ПАРСЕР ПРЕПОДАВАТЕЛЯ (исправленный) =========================
def parse_teacher_schedule(teacher_name: str, start_date: datetime, end_date: datetime):
    if teacher_name not in TEACHER_MAP:
        st.error(f"Преподаватель {teacher_name} не найден.")
        return pd.DataFrame()

    teacher_id = TEACHER_MAP[teacher_name]
    all_lessons = []
    
    days_ahead = 0 - start_date.weekday()
    if days_ahead < 0:
        days_ahead += 7
    current = start_date + timedelta(days=days_ahead)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 1
    base_url = f"https://ruz.spbstu.ru/teachers/{teacher_id}"

    while current <= end_date:
        week_count += 1
        url = f"{base_url}?date={current.strftime('%Y-%m-%d')}"
        status_text.text(f"Обработка недели {week_count} из {total_weeks} (дата {current.strftime('%d.%m.%Y')})")

        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for day in soup.find_all('li', class_='schedule__day'):
                    date_elem = day.find('div', class_='schedule__date')
                    if not date_elem:
                        continue
                    date_text = date_elem.text.strip()
                    try:
                        lesson_date = datetime.strptime(date_text, "%d.%m.%Y")
                        if lesson_date < start_date or lesson_date > end_date:
                            continue
                    except:
                        pass

                    for lesson in day.find_all('li', class_='lesson'):
                        subject = ""
                        subject_elem = lesson.find('div', class_='lesson__subject')
                        if subject_elem:
                            spans = subject_elem.find_all('span')
                            if spans and len(spans) > 2:
                                subject = spans[-1].text.strip()

                        lesson_type = lesson.find('div', class_='lesson__type')
                        lesson_type = lesson_type.text.strip() if lesson_type else ""

                        time_str = lesson.find('span', class_='lesson__time')
                        time_str = time_str.text.strip() if time_str else ""

                        groups = []
                        groups_elem = lesson.find('div', class_='lesson-groups__list')
                        if groups_elem:
                            for link in groups_elem.find_all('a', class_='lesson__link'):
                                groups.append(link.text.strip())

                        place = parse_place(lesson.find('div', class_='lesson__places'))

                        teacher_element = lesson.find('div', class_='lesson__teachers')
                        is_our_teacher = False
                        if teacher_element:
                            if any(f'/teachers/{teacher_id}' in a.get('href', '') for a in teacher_element.find_all('a')):
                                is_our_teacher = True

                        if is_our_teacher and subject:
                            all_lessons.append({
                                "Дата": date_text,
                                "Время": time_str,
                                "Дисциплина": subject,
                                "Тип занятия": lesson_type,
                                "Группы": ', '.join(groups),
                                "Преподаватель": teacher_name,
                                "Место": place
                            })
            progress_bar.progress(min(week_count / total_weeks, 1.0))
            time.sleep(12)
        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {e}")

        current += timedelta(weeks=1)

    status_text.empty()
    return pd.DataFrame(all_lessons)

# ========================= ФУНКЦИЯ ДЛЯ ПОСТРОЕНИЯ ТАБЛИЦЫ-КАЛЕНДАРЯ =========================
def build_calendar_table(schedule_dfs, start_date, end_date, hour_start=9, hour_end=21):
    """
    Строит HTML-таблицу с временными слотами (часами) и датами.
    schedule_dfs: список DataFrame с расписаниями выбранных групп и преподавателей
    """
    if not schedule_dfs:
        return "<p>Нет данных для отображения</p>"
    
    # Объединяем все расписания
    combined = pd.concat(schedule_dfs, ignore_index=True)
    # Приводим даты к единому формату
    combined['Дата_obj'] = pd.to_datetime(combined['Дата'], format='%d.%m.%Y', errors='coerce')
    # Отбираем только нужный диапазон
    mask = (combined['Дата_obj'] >= pd.Timestamp(start_date)) & (combined['Дата_obj'] <= pd.Timestamp(end_date))
    combined = combined[mask].copy()
    if combined.empty:
        return "<p>Нет занятий за выбранный период</p>"
    
    # Список уникальных дат в диапазоне
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    date_strs = [d.strftime('%d.%m.%Y') for d in date_range]
    
    # Часовые слоты
    slots = [f"{h:02d}:00-{h+1:02d}:00" for h in range(hour_start, hour_end)]
    
    # Для каждой даты и каждого слота собираем информацию о занятиях
    cell_data = {}
    for date_obj in date_range:
        date_str = date_obj.strftime('%d.%m.%Y')
        day_lessons = combined[combined['Дата_obj'] == date_obj]
        cell_data[date_str] = {}
        for slot in slots:
            slot_hour = int(slot.split(':')[0])
            slot_start = datetime.strptime(f"{slot_hour:02d}:00", "%H:%M")
            slot_end = datetime.strptime(f"{slot_hour+1:02d}:00", "%H:%M")
            # Ищем занятия, пересекающиеся со слотом
            intersecting = []
            for _, row in day_lessons.iterrows():
                time_str = row['Время']
                if '–' not in time_str:
                    continue
                start_str, end_str = time_str.split('–')
                start_str = start_str.strip()
                end_str = end_str.strip()
                try:
                    start_time = datetime.strptime(start_str, "%H:%M")
                    end_time = datetime.strptime(end_str, "%H:%M")
                except:
                    continue
                # Пересечение интервалов
                if start_time < slot_end and end_time > slot_start:
                    # Формируем текст для ячейки
                    subject = row['Дисциплина']
                    lesson_type = row['Тип занятия']
                    teacher = row.get('Преподаватель', row.get('Группы', ''))
                    place = row.get('Место', '')
                    intersecting.append(f"{subject} ({lesson_type})<br>{teacher}<br>{place}")
            if intersecting:
                cell_data[date_str][slot] = "<br>".join(intersecting)
            else:
                cell_data[date_str][slot] = "СВОБОДНО"
    
    # Строим HTML-таблицу с CSS для подсветки
    html = '<div style="overflow-x: auto;"><table style="border-collapse: collapse; width: 100%; font-size: 12px;">'
    # Заголовок (даты)
    html += '<thead><tr><th style="border: 1px solid #ddd; padding: 8px;">Время</th>'
    for d in date_strs:
        # Форматируем дату: день недели + число
        dt = datetime.strptime(d, '%d.%m.%Y')
        weekday = dt.strftime('%a')
        html += f'<th style="border: 1px solid #ddd; padding: 8px;">{weekday}<br>{d}</th>'
    html += '</tr></thead><tbody>'
    
    # Строки для каждого слота
    for slot in slots:
        html += f'<tr><td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{slot}</td>'
        for d in date_strs:
            content = cell_data.get(d, {}).get(slot, "Нет данных")
            # Цвет фона: если "СВОБОДНО" - зелёный, иначе красный/оранжевый
            if "СВОБОДНО" in content:
                bg_color = "#d4edda"  # светло-зелёный
                text_color = "#155724"
            else:
                bg_color = "#f8d7da"  # светло-красный
                text_color = "#721c24"
            html += f'<td style="border: 1px solid #ddd; padding: 8px; background-color: {bg_color}; color: {text_color};">{content}</td>'
        html += '</tr>'
    
    html += '</tbody></table></div>'
    return html

# ========================= ИНТЕРФЕЙС =========================
tab1, tab3, tab2 = st.tabs(["📥 Вывод расписания", "📊 Статистика", "🔍 Поиск свободных окон"])

# ====================== ВКЛАДКА 1: ВЫВОД РАСПИСАНИЯ ======================
with tab1:
    st.subheader("📥 Вывод расписания")

    mode = st.radio("Что выводим?", ["Расписание группы", "Расписание преподавателя"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", datetime(2026, 2, 1))
    with col2:
        end_date = st.date_input("Дата окончания", datetime(2026, 5, 25))

    if mode == "Расписание группы":
        group_human = st.selectbox("Выберите группу", list(GROUP_MAP.keys()))
        if st.button("🚀 Показать расписание группы", type="primary"):
            with st.spinner("Парсинг..."):
                df = parse_group_schedule(group_human, start_date, end_date)
                if not df.empty:
                    st.session_state.schedule_data = {f"Группа {group_human}": df}
                    st.success(f"✅ Загружено {len(df)} занятий")
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        st.dataframe(df[df['Дата'] == date])
    else:
        teacher_name = st.selectbox("Выберите преподавателя", list(TEACHER_MAP.keys()))
        if st.button("🚀 Показать расписание преподавателя", type="primary"):
            with st.spinner("Парсинг..."):
                df = parse_teacher_schedule(teacher_name, start_date, end_date)
                if not df.empty:
                    st.session_state.schedule_data = {f"Преподаватель {teacher_name}": df}
                    st.success(f"✅ Загружено {len(df)} занятий")
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        st.dataframe(df[df['Дата'] == date])

# ====================== ВКЛАДКА 2: СТАТИСТИКА ======================
with tab3:
    st.subheader("📊 Статистика")
    if 'schedule_data' in st.session_state and st.session_state.schedule_data:
        all_dfs = list(st.session_state.schedule_data.values())
        combined = pd.concat(all_dfs, ignore_index=True)
        st.metric("Всего занятий", len(combined))
        st.metric("Период", f"{combined['Дата'].min()} — {combined['Дата'].max()}")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**По типам занятий:**")
            st.dataframe(combined['Тип занятия'].value_counts())
        with col2:
            st.write("**По преподавателям:**")
            st.dataframe(combined['Преподаватель'].value_counts())
    else:
        st.info("Загрузите расписание на вкладке 'Вывод расписания'")

# ====================== ВКЛАДКА 3: ПОИСК СВОБОДНЫХ ОКОН ======================
with tab2:
    st.subheader("🔍 Поиск свободных окон (таблица-календарь)")

    st.write("**Выберите группы и преподавателей:**")
    selected_groups = st.multiselect("Группы", options=list(GROUP_MAP.keys()))
    selected_teachers = st.multiselect("Преподаватели", options=list(TEACHER_MAP.keys()))

    col_period1, col_period2 = st.columns(2)
    with col_period1:
        search_start = st.date_input("Начало периода поиска", datetime(2026, 2, 1), key="search_start")
    with col_period2:
        search_end = st.date_input("Конец периода поиска", datetime(2026, 2, 28), key="search_end")

    if st.button("🔎 Построить календарь", type="primary"):
        if not selected_groups and not selected_teachers:
            st.warning("Выберите хотя бы одну группу или преподавателя")
        else:
            with st.spinner("Загрузка расписаний..."):
                schedule_dfs = []
                if selected_groups:
                    for g in selected_groups:
                        df = parse_group_schedule(g, search_start, search_end)
                        if not df.empty:
                            schedule_dfs.append(df)
                if selected_teachers:
                    for t in selected_teachers:
                        df = parse_teacher_schedule(t, search_start, search_end)
                        if not df.empty:
                            schedule_dfs.append(df)
            
            if not schedule_dfs:
                st.warning("Не удалось загрузить расписания для выбранных элементов.")
            else:
                # Строим календарь
                html_table = build_calendar_table(schedule_dfs, search_start, search_end, hour_start=9, hour_end=21)
                st.markdown(html_table, unsafe_allow_html=True)
                st.caption("Зелёные ячейки — свободные слоты (нет занятий у выбранных групп и преподавателей). Красные — занято.")

st.caption("Версия 4.0 • Таблица-календарь с часовыми слотами • Исправлен парсинг дат")
