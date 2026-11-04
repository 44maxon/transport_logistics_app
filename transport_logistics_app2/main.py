# -*- coding: utf-8 -*-
"""Учебное приложение «Транспортная логистика» на Python + Kivy.

Модель: один автомобиль, координаты в условных километрах, евклидово расстояние,
временные окна и суммарное ограничение грузоподъёмности.
Для небольшого числа точек применяется полный перебор маршрутов.
"""

from itertools import permutations
from math import hypot

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle

Window.clearcolor = (0.94, 0.96, 0.98, 1)
Window.minimum_width, Window.minimum_height = 360, 600


def minutes_from_time(value):
    """Преобразует HH:MM в минуты от начала суток."""
    parts = value.strip().split(':')
    if len(parts) != 2:
        raise ValueError('Время укажите в формате ЧЧ:ММ')
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError('Некорректное время')
    return h * 60 + m


def time_text(value):
    value = int(round(value)) % (24 * 60)
    return f'{value // 60:02d}:{value % 60:02d}'


class LogisticsApp(App):
    def build(self):
        self.title = 'Транспортная логистика'
        self.deliveries = []
        self.fields = {}

        root = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        header = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(66),
                           padding=(dp(14), dp(7)), spacing=dp(2))
        with header.canvas.before:
            Color(0.07, 0.20, 0.34, 1)
            header_bg = RoundedRectangle(pos=header.pos, size=header.size, radius=[dp(14)])
        header.bind(pos=lambda obj, *_: setattr(header_bg, 'pos', obj.pos),
                    size=lambda obj, *_: setattr(header_bg, 'size', obj.size))
        header.add_widget(Label(text='ТРАНСПОРТНАЯ ЛОГИСТИКА', bold=True,
                                font_size='18sp', color=(1, 1, 1, 1)))
        header.add_widget(Label(text='Планирование и расчёт маршрутов доставки',
                                font_size='11sp', color=(0.78, 0.87, 0.95, 1)))
        root.add_widget(header)

        scroll = ScrollView()
        body = BoxLayout(orientation='vertical', spacing=dp(10),
                         size_hint_y=None, padding=(0, 0, 0, dp(12)))
        body.bind(minimum_height=body.setter('height'))
        scroll.add_widget(body)
        root.add_widget(scroll)

        body.add_widget(self.section('ПАРАМЕТРЫ АВТОМОБИЛЯ'))
        vehicle = GridLayout(cols=2, spacing=dp(6), size_hint_y=None,
                             row_default_height=dp(42), row_force_default=True)
        vehicle.height = dp(42 * 5 + 24)
        self.add_field(vehicle, 'capacity', 'Грузоподъёмность, кг', '1500')
        self.add_field(vehicle, 'speed', 'Средняя скорость, км/ч', '40')
        self.add_field(vehicle, 'start_time', 'Начало маршрута, ЧЧ:ММ', '08:00')
        self.add_field(vehicle, 'tariff_km', 'Тариф, руб/км', '15')
        self.add_field(vehicle, 'tariff_hour', 'Тариф, руб/час', '300')
        body.add_widget(vehicle)

        body.add_widget(self.section('СКЛАД / ТОЧКА СТАРТА'))
        depot = GridLayout(cols=2, spacing=dp(6), size_hint_y=None,
                           row_default_height=dp(42), row_force_default=True)
        depot.height = dp(84)
        self.add_field(depot, 'depot_x', 'Координата X, км', '0')
        self.add_field(depot, 'depot_y', 'Координата Y, км', '0')
        body.add_widget(depot)

        body.add_widget(self.section('НОВАЯ ДОСТАВКА'))
        delivery = GridLayout(cols=2, spacing=dp(6), size_hint_y=None,
                              row_default_height=dp(42), row_force_default=True)
        delivery.height = dp(42 * 6 + 30)
        self.add_field(delivery, 'name', 'Название точки', 'Точка 1')
        self.add_field(delivery, 'weight', 'Вес груза, кг', '300')
        self.add_field(delivery, 'x', 'Координата X, км', '5')
        self.add_field(delivery, 'y', 'Координата Y, км', '3')
        self.add_field(delivery, 'window_start', 'Окно с, ЧЧ:ММ', '09:00')
        self.add_field(delivery, 'window_end', 'Окно до, ЧЧ:ММ', '12:00')
        body.add_widget(delivery)

        add_btn = Button(text='＋ Добавить точку доставки', size_hint_y=None,
                         height=dp(46), background_normal='',
                         background_color=(0.10, 0.40, 0.68, 1), bold=True, font_size='14sp')
        add_btn.bind(on_release=self.add_delivery)
        body.add_widget(add_btn)

        self.points_label = Label(text='Точки доставки пока не добавлены',
                                  size_hint_y=None, height=dp(60),
                                  color=(0.16, 0.22, 0.30, 1),
                                  halign='left', valign='middle')
        self.points_label.bind(size=lambda *_: setattr(self.points_label, 'text_size', self.points_label.size))
        body.add_widget(self.points_label)

        controls = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(48))
        calc = Button(text='Рассчитать маршрут', background_normal='',
                      background_color=(0.08, 0.53, 0.37, 1), bold=True, font_size='14sp')
        calc.bind(on_release=self.calculate)
        clear = Button(text='Очистить точки', background_normal='',
                       background_color=(0.38, 0.45, 0.54, 1), bold=True, font_size='13sp')
        clear.bind(on_release=self.clear_deliveries)
        controls.add_widget(calc)
        controls.add_widget(clear)
        body.add_widget(controls)

        body.add_widget(self.section('КРИТЕРИЙ ОПТИМИЗАЦИИ'))
        self.fields['criterion'] = Spinner(text='Время', values=('Время', 'Расстояние', 'Стоимость'),
                                           size_hint_y=None, height=dp(42),
                                           background_normal='', background_color=(1, 1, 1, 1),
                                           color=(0.08, 0.12, 0.18, 1))
        body.add_widget(self.fields['criterion'])

        body.add_widget(self.section('РЕЗУЛЬТАТ РАСЧЁТА'))
        self.result = Label(text='Добавьте доставки и нажмите «Рассчитать маршрут».',
                            size_hint_y=None, height=dp(190),
                            color=(0.08, 0.19, 0.32, 1),
                            halign='left', valign='top')
        self.result.bind(size=lambda *_: setattr(self.result, 'text_size', (self.result.width, None)))
        body.add_widget(self.result)

        return root

    def section(self, text):
        return Label(text=text, size_hint_y=None, height=dp(28), bold=True,
                     font_size='13sp', color=(0.08, 0.29, 0.48, 1),
                     halign='left', valign='middle')

    def add_field(self, layout, key, caption, default):
        label = Label(text=caption, color=(0.18, 0.24, 0.31, 1),
                      halign='left', valign='middle', font_size='12sp', bold=True)
        label.bind(size=lambda obj, *_: setattr(obj, 'text_size', obj.size))
        field = TextInput(text=default, multiline=False, size_hint_y=None,
                          height=dp(40), font_size='14sp',
                          background_normal='', background_active='',
                          background_color=(1, 1, 1, 1), foreground_color=(0.08, 0.12, 0.18, 1),
                          padding=(dp(8), dp(10)))
        layout.add_widget(label)
        layout.add_widget(field)
        self.fields[key] = field

    def value(self, key):
        return self.fields[key].text.strip()

    def add_delivery(self, *_):
        try:
            item = {
                'name': self.value('name') or f'Точка {len(self.deliveries) + 1}',
                'weight': float(self.value('weight')),
                'x': float(self.value('x')),
                'y': float(self.value('y')),
                'start': minutes_from_time(self.value('window_start')),
                'end': minutes_from_time(self.value('window_end')),
            }
            if item['weight'] <= 0:
                raise ValueError('Вес груза должен быть больше нуля')
            if item['start'] > item['end']:
                raise ValueError('Начало временного окна позже его окончания')
            if len(self.deliveries) >= 8:
                raise ValueError('В учебной версии допускается не более 8 точек')
            self.deliveries.append(item)
            self.update_points()
            self.result.text = f'Добавлена точка «{item["name"]}». Можно добавить следующую.'
        except ValueError as exc:
            self.result.text = f'Ошибка ввода: {exc}'

    def update_points(self):
        if not self.deliveries:
            self.points_label.text = 'Точки доставки пока не добавлены'
        else:
            lines = [f'{i + 1}. {p["name"]} — {p["weight"]:g} кг, '
                     f'{time_text(p["start"])}–{time_text(p["end"])}'
                     for i, p in enumerate(self.deliveries)]
            self.points_label.text = 'Добавленные доставки:\n' + '\n'.join(lines)
            self.points_label.height = dp(32 + 22 * len(lines))

    def clear_deliveries(self, *_):
        self.deliveries.clear()
        self.update_points()
        self.result.text = 'Список доставок очищен.'

    def calculate(self, *_):
        if not self.deliveries:
            self.result.text = 'Сначала добавьте хотя бы одну точку доставки.'
            return
        try:
            capacity = float(self.value('capacity'))
            speed = float(self.value('speed'))
            depot_x, depot_y = float(self.value('depot_x')), float(self.value('depot_y'))
            tariff_km = float(self.value('tariff_km'))
            tariff_hour = float(self.value('tariff_hour'))
            departure = minutes_from_time(self.value('start_time'))
            if capacity <= 0 or speed <= 0 or tariff_km < 0 or tariff_hour < 0:
                raise ValueError('Проверьте грузоподъёмность, скорость и тарифы')
        except ValueError as exc:
            self.result.text = f'Ошибка параметров: {exc}'
            return

        total_weight = sum(p['weight'] for p in self.deliveries)
        if total_weight > capacity:
            self.result.text = (f'Маршрут не построен: суммарный груз {total_weight:g} кг '
                                f'превышает грузоподъёмность {capacity:g} кг.')
            return

        def distance(a, b):
            return hypot(a['x'] - b['x'], a['y'] - b['y'])

        depot = {'x': depot_x, 'y': depot_y}
        best = None
        best_data = None
        for order in permutations(self.deliveries):
            current = depot
            clock = float(departure)
            km = 0.0
            schedule = []
            valid = True
            for point in order:
                leg = distance(current, point)
                km += leg
                arrival = clock + leg / speed * 60
                service_start = max(arrival, point['start'])
                if service_start > point['end']:
                    valid = False
                    break
                service_end = service_start + 10  # условное обслуживание 10 минут
                schedule.append((point, arrival, service_start, service_end, leg))
                clock = service_end
                current = point
            if not valid:
                continue
            back = distance(current, depot)
            km += back
            finish = clock + back / speed * 60
            drive_hours = km / speed
            cost = km * tariff_km + drive_hours * tariff_hour
            criterion = self.value('criterion') if 'criterion' in self.fields else 'Время'
            score = {'Расстояние': km, 'Время': finish - departure, 'Стоимость': cost}.get(criterion, finish - departure)
            if best is None or score < best:
                best = score
                best_data = (order, schedule, km, finish, cost, back)

        if best_data is None:
            self.result.text = ('Подходящий маршрут не найден. Проверьте временные окна, '
                                'время выезда и скорость автомобиля.')
            return

        order, schedule, km, finish, cost, back = best_data
        lines = ['Оптимальный маршрут:', 'Склад']
        for i, (point, arrival, start, end, leg) in enumerate(schedule, 1):
            wait = max(0, start - arrival)
            lines.append(f'{i}. {point["name"]}: прибытие {time_text(arrival)}, '
                         f'доставка {time_text(start)}–{time_text(end)}')
            if wait > 0.5:
                lines.append(f'   Ожидание: {int(round(wait))} мин.')
        lines.append('Возврат на склад')
        lines.append('')
        lines.append(f'Общий пробег: {km:.2f} км')
        lines.append(f'Завершение маршрута: {time_text(finish)}')
        lines.append(f'Общее время: {(finish - departure) / 60:.2f} ч')
        lines.append(f'Стоимость по тарифам: {cost:.2f} руб.')
        lines.append(f'Загрузка: {total_weight:g} / {capacity:g} кг')
        lines.append('Алгоритм: полный перебор перестановок с проверкой ограничений.')
        self.result.text = '\n'.join(lines)
        self.result.height = dp(max(230, 24 * len(lines)))


if __name__ == '__main__':
    LogisticsApp().run()
