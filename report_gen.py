import asyncio
import datetime
import os

from fpdf import FPDF
import matplotlib.pyplot as plt
from async_sqlite import get_data_for_report


async def generate_pdf_report(room_id):
    data = await get_data_for_report(room_id)

    total_tasks_added = data['total_tasks_added']
    total_tasks_completed = data['total_tasks_completed']
    total_tasks_incomplete = data['total_tasks_incomplete']
    employees_completed_tasks = data['employees_completed_tasks']
    employees = data['employees']
    await draw_room_pie(total_tasks_incomplete, employees_completed_tasks, room_id)
    await draw_bar_for_employees(employees, room_id)
    await draw_daily_graph(data['daily_graf'])
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('DejaVu', '', 'fpdf_font/DejaVuSansCondensed.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', 'fpdf_font/DejaVuSansCondensed-Bold.ttf', uni=True)

    pdf.set_font('DejaVu', '', 25)

    pdf.cell(150, 20, txt="Общий", ln=True, align="R")
    pdf.set_font('DejaVu', '', 12)

    x_now = pdf.get_x()
    y_now = pdf.get_y()

    pdf.image(f'{room_id}_pie.png', x=x_now - 10, y=y_now - 40, w=120, h=120)
    pdf.set_xy(x_now + 110, y_now)
    pdf.cell(200, 7, txt=f'Добавленных задач за месяц: {total_tasks_added}', ln=True)
    pdf.set_xy(x_now + 110, pdf.get_y())
    pdf.cell(200, 7, txt=f'Выполненных задач: {total_tasks_completed}', ln=True)
    pdf.set_xy(x_now + 110, pdf.get_y())
    pdf.cell(200, 7, txt=f'Не выполненных задач: {total_tasks_incomplete}', ln=True)
    pdf.set_xy(x_now - 5, pdf.get_y()+50)
    pdf.image('daily_graph.png', w=200, h=150)
    pdf.set_font('DejaVu', '', 25)
    pdf.set_y(pdf.get_y() + 50)
    pdf.cell(200, 10, txt="По сотрудникам", ln=True, align="C")
    pdf.set_font('DejaVu', '', 12)
    pdf.image(f'{room_id}_bar.png', y=pdf.get_y(), w=180, h=108)
    pdf.set_y(pdf.get_y() + 120)

    html = """
    <table>
      <tr>
        <th>Имя</th>
        <th>Добавленных задач</th>
        <th>Выполненных</th>
        <th>Не выполненных</th>
        <th>% выполнения</th>
      </tr>"""

    for employee in employees:
        completed_tasks = employees[employee][1]
        total_tasks = int(employees[employee][1]) + int(employees[employee][2])
        completion_percentage = (completed_tasks / total_tasks) * 100 if employee[4] else 0

        html += f"""
      <tr>
        <td>{employees[employee][0]}</td>
        <td>{total_tasks}</td>
        <td>{completed_tasks}</td>
        <td>{employees[employee][2]}</td>
        <td>{completion_percentage}</td>
      </tr>
    """
    html += """
    </table>
    """
    pdf.write_html(text=html)
    pdf.output(f"report_{room_id}.pdf", dest='S')
    os.remove(f'{room_id}_pie.png')
    os.remove(f'{room_id}_bar.png')
    os.remove('daily_graph.png')


async def draw_room_pie(total_tasks_incomplete, employees_completed_tasks, room_id):
    plt.figure(figsize=(8, 8))

    sizes = []
    labels = []
    if total_tasks_incomplete != 0:
        sizes.append(total_tasks_incomplete)
        labels.append('Не выполнено')
    [sizes.append(i[1]) for i in employees_completed_tasks.values() if i[1] != 0]

    [labels.append(i[0]) for i in employees_completed_tasks.values() if i[1] != 0]

    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 12})
    plt.savefig(f'{room_id}_pie.png')
    plt.close()


async def draw_bar_for_employees(employees_data, room_id):

    employees = [employees_data[i][0] for i in employees_data]
    total_tasks = [int(employees_data[i][1]) + int(employees_data[i][2]) for i in employees_data]
    completed_tasks = [employees_data[i][1] for i in employees_data]

    print(employees,total_tasks,completed_tasks)
    plt.figure(figsize=(10, 6))
    plt.bar(employees, total_tasks, color='skyblue', label='Всего дел')
    plt.bar(employees, completed_tasks, color='orange', label='Выполнено дел')
    plt.ylabel('Количество задач')
    plt.legend()
    plt.tight_layout()

    plt.savefig(f'{room_id}_bar.png')
    plt.close()


async def draw_daily_graph(data):
    days = [date[8:] for date in data.keys()]

    employees = sorted(set(employee for day_data in data.values() for employee in day_data if employee != 'incomplete'))

    completed_tasks = [[] for _ in range(len(employees))]
    incomplete_tasks = []

    # Извлекаем имена сотрудников из данных
    employee_names = {employee: day_data[employee][0] for day_data in data.values() for employee in day_data if employee != 'incomplete'}

    for day_data in data.values():
        for idx, employee in enumerate(employees):
            if employee in day_data:
                completed_tasks[idx].append(day_data[employee][1])
            else:
                completed_tasks[idx].append(0)
        incomplete_tasks.append(day_data.get('incomplete', 0))

    fig, ax = plt.subplots()

    # Столбики для выполненных задач
    bottom = [0] * len(days)
    for idx, tasks in enumerate(completed_tasks):
        ax.bar(days, tasks, bottom=bottom, label=employee_names[employees[idx]])
        bottom = [sum(x) for x in zip(bottom, tasks)]

    # Столбик для невыполненных задач
    ax.bar(days, incomplete_tasks, bottom=bottom, color='grey', label='Не выполнено')
    month_names_ru = {
        1: "Январь",
        2: "Февраль",
        3: "Март",
        4: "Апрель",
        5: "Май",
        6: "Июнь",
        7: "Июль",
        8: "Август",
        9: "Сентябрь",
        10: "Октябрь",
        11: "Ноябрь",
        12: "Декабрь"
    }
    current_date = datetime.datetime.now()

    # Get number of the previous month
    previous_month = current_date.month - 1 if current_date.month > 1 else 12

    # Get the name of the previous month
    previous_month_name = month_names_ru[previous_month]
    ax.set_xlabel(previous_month_name)
    ax.set_ylabel('Количество задач')
    ax.set_title('Статистика выполненных и невыполненных задач по дням')
    ax.legend()

    plt.xticks(ha='right')
    plt.tight_layout()
    plt.savefig('daily_graph.png')
    plt.close()
