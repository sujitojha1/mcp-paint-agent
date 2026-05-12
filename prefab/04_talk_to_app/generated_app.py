from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Badge, Card, CardContent, CardHeader, CardTitle,
    Checkbox, Column, H1, H3, Muted, Progress, Ring, Row,
    Tab, Tabs, Text,
)
from prefab_ui.components.charts import BarChart, ChartSeries, PieChart, Sparkline

initial_state = {'h_0_0': True, 'h_0_1': True, 'h_0_2': True, 'h_0_3': True, 'h_0_4': False, 'h_0_5': False, 'h_0_6': False, 'h_1_0': True, 'h_1_1': True, 'h_1_2': True, 'h_1_3': True, 'h_1_4': True, 'h_1_5': True, 'h_1_6': True, 'h_2_0': True, 'h_2_1': True, 'h_2_2': True, 'h_2_3': True, 'h_2_4': False, 'h_2_5': True, 'h_2_6': False}

with PrefabApp(state=initial_state, css_class="max-w-4xl mx-auto p-6") as app:
    with Card():
        with CardHeader():
            CardTitle('Stock Tracker')
            Muted("Tracking 3 habits over the last 7 days.")
        with CardContent():
            with Tabs(value="today"):
                with Tab("Today", value="today"):
                    with Column(gap=5):
                        with Column(gap=2):
                            H3("Tick today's habits")
                            with Row(gap=3):
                                Checkbox(name="h_0_0")
                                Text('Industry Splits')
                            with Row(gap=3):
                                Checkbox(name="h_1_0")
                                Text('Returns')
                            with Row(gap=3):
                                Checkbox(name="h_2_0")
                                Text('Concerns')
                        with Column(gap=2):
                            H3("At a glance")
                            with Row(gap=2):
                                Badge("Total: 16", variant="default")
                                Badge("Best day: 3/3", variant="success")
                                Badge("Habits: 3", variant="default")
                                Badge("Days: 7", variant="default")
                with Tab("This Week", value="week"):
                    with Column(gap=5):
                        with Column(gap=2):
                            H3("Check-ins per day")
                            BarChart(data=[{'day': 'Mon', 'done': 3}, {'day': 'Tue', 'done': 3}, {'day': 'Wed', 'done': 3}, {'day': 'Thu', 'done': 3}, {'day': 'Fri', 'done': 1}, {'day': 'Sat', 'done': 2}, {'day': 'Sun', 'done': 1}],
                                     series=[ChartSeries(data_key="done", label="Done")],
                                     x_axis="day", show_legend=False)
                        with Column(gap=2):
                            H3("Last 7 days")
                            with Row(gap=2):
                                Text("              ")
                                Badge('Mon', variant="default")
                                Badge('Tue', variant="default")
                                Badge('Wed', variant="default")
                                Badge('Thu', variant="default")
                                Badge('Fri', variant="default")
                                Badge('Sat', variant="default")
                                Badge('Sun', variant="default")
                            with Row(gap=2):
                                Text('Industry Splits')
                                Checkbox(name="h_0_0")
                                Checkbox(name="h_0_1")
                                Checkbox(name="h_0_2")
                                Checkbox(name="h_0_3")
                                Checkbox(name="h_0_4")
                                Checkbox(name="h_0_5")
                                Checkbox(name="h_0_6")
                            with Row(gap=2):
                                Text('Returns')
                                Checkbox(name="h_1_0")
                                Checkbox(name="h_1_1")
                                Checkbox(name="h_1_2")
                                Checkbox(name="h_1_3")
                                Checkbox(name="h_1_4")
                                Checkbox(name="h_1_5")
                                Checkbox(name="h_1_6")
                            with Row(gap=2):
                                Text('Concerns')
                                Checkbox(name="h_2_0")
                                Checkbox(name="h_2_1")
                                Checkbox(name="h_2_2")
                                Checkbox(name="h_2_3")
                                Checkbox(name="h_2_4")
                                Checkbox(name="h_2_5")
                                Checkbox(name="h_2_6")
                with Tab("Stats", value="stats"):
                    with Column(gap=5):
                        with Column(gap=2):
                            H3("Check-ins by habit")
                            PieChart(data=[{'habit': 'Industry Splits', 'count': 4}, {'habit': 'Returns', 'count': 7}, {'habit': 'Concerns', 'count': 5}], data_key="count", name_key="habit", show_legend=True)
                        with Column(gap=3):
                            H3("Weekly progress per habit")
                            with Column(gap=1):
                                Text('Industry Splits')
                                Progress(value=57)
                            with Column(gap=1):
                                Text('Returns')
                                Progress(value=100)
                            with Column(gap=1):
                                Text('Concerns')
                                Progress(value=71)
                        with Column(gap=2):
                            H3("At a glance")
                            with Row(gap=2):
                                Badge("Total: 16", variant="default")
                                Badge("Best day: 3/3", variant="success")
                                Badge("Habits: 3", variant="default")
                                Badge("Days: 7", variant="default")
