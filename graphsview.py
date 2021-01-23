"""
UI implementation of the graphs view.
"""

__author__ = 'Holger Fleischmann'
__copyright__ = 'Copyright 2018, Holger Fleischmann, Bavaria/Germany'
__license__ = 'Apache License 2.0'

from kivy.uix.boxlayout import BoxLayout
from kivy_garden.graph import Graph, LinePlot
from kivy.clock import Clock

from history import SignalHistory
import time


class GraphsCanvas(Graph):

    def __init__(self, **kwargs):
        self.allowed_min_y = -15
        self.allowed_max_y = 60
        # note: ticks_minor means the number of subdivisions 
        super().__init__(x_ticks_minor=6,
                         x_ticks_major=3600,
                         xlabel='Zeit',
                         y_ticks_major=5,
                         y_ticks_minor=5,
                         ylabel='Temperaturen °C',
                         xmin=0,
                         xmax=3600,
                         ymin=self.allowed_min_y,
                         ymax=self.allowed_max_y)


class GestureDetector(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__touches = []
        self.pinch_continue = False
        self.__max_touches = 0

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.pinch_continue = False
            touch.grab(self)
            self.__touches.append(touch)
            self.__max_touches += 1
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is not self or len(self.__touches) != 2:
            return super().on_touch_move(touch)
        t1 = self.__touches[0]
        t2 = self.__touches[1]
        # ox, oy are only consistent after seconds touch point moved:
        if touch != t2:
            return
        self.on_pinch(
            self.pinch_continue,
            ((t1.ox + t2.ox) / 2., (t1.oy + t2.oy) / 2.),
            ((t1.x + t2.x) / 2., (t1.y + t2.y) / 2.),
            (abs(t1.ox - t2.ox), abs(t1.oy - t2.oy)),
            (abs(t1.x - t2.x), abs(t1.y - t2.y))
        )
        self.pinch_continue = True
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:

            if len(self.__touches) == 1:
                if self.__max_touches == 1 and touch.is_double_tap:
                    self.on_double_tap((touch.x, touch.y))
                self.__max_touches = 0

            self.pinch_continue = False
            touch.ungrab(self)
            self.__touches.remove(touch)
        return super().on_touch_up(touch)

    def on_pinch(self, pinch_continue, orig_center, center, orig_size, size):
        pass

    def on_double_tap(self, center):
        pass


class GraphsScreen(GestureDetector):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def use_signals_config(self, signal_sources_config):
        self.graph_labels = []

        self.history = SignalHistory()
        if 'history_max' in signal_sources_config:
            self.history.max_seconds = signal_sources_config['history_max']
        if 'history_delta' in signal_sources_config:
            self.history.delta_seconds = signal_sources_config['history_delta']

        self.plots = []
        self.graph_visible = []

        for group in signal_sources_config['groups']:
            group_label = group['label']
            for source in group['sources']:
                self.graph_labels.append(group_label + ' ' + source.label)
                self.history.add_source(source)
                self.graph_visible.append(source.with_graph)
                plot = LinePlot(color=source.color)
                self.plots.append(plot)

        for source_plot in sorted(zip(self.history.sources, self.plots), key=lambda sp: sp[0].z_order):
            self.ids.graphs_canvas.add_plot(source_plot[1])

        self.history.write_to_csv('csv/signals')
        self.history.load_from_csv_files()
        self.history.start()

        self.x_range = self.history.max_seconds
        self.x_max = None

        Clock.schedule_once(self.update_graphs, 0.)

    def update_graphs(self, dt):
        with self.history:
            if self.x_max is None:
                now = time.time()
                self.ids.graphs_canvas.xmax = now + 240  # workaround for cut-off right graph edge
                self.ids.graphs_canvas.xmin = now - self.x_range
            else:
                self.ids.graphs_canvas.xmax = self.x_max
                self.ids.graphs_canvas.xmin = self.x_max - self.x_range

            for (source, plot, visible) in zip(self.history.sources, self.plots, self.graph_visible):
                if visible:
                    plot.points = self.history.get_values(source)
                else:
                    plot.points = []

        Clock.schedule_once(self.update_graphs, self.history.delta_seconds / 2)
        pass

    def on_double_tap(self, center):
        graph = self.ids.graphs_canvas
        pos = graph.to_data(center[0], center[1])
        if self.x_max is None:
            # zoom in
            self.x_range = self.history.max_seconds / 12
            self.x_max = min(time.time(), pos[0] + self.x_range / 2)
        else:
            # reset zoom
            self.x_range = self.history.max_seconds
            self.x_max = None
        self.update_graphs(None)

    def on_pinch(self, pinch_continue, orig_center, center, orig_size, size):
        graph = self.ids.graphs_canvas
        # if not pinch_continue:
        #    print()
        #    print()
        #    print()
        # print(str(pinch_continue) + " oc=" + str(orig_center) + " os=" + str(orig_size) + " c=" + str(center) + " s=" + str(size))
        if pinch_continue:
            new_center_y = (self.begin_min_y + self.begin_max_y) / 2.
            new_center_y -= (
                    graph.to_data(0, center[1] - graph.y)[1]
                    - graph.to_data(0, orig_center[1] - graph.y)[1]
            )
            new_delta_y = self.begin_max_y - self.begin_min_y
            if orig_size[1] > 50:
                new_delta_y = new_delta_y * (orig_size[1] / max(1, size[1]))
                new_delta_y = (max(5, new_delta_y) // 5 + 1) * 5
            # print('new center=' + str(new_center_y) + ' delta=' + str(new_delta_y))
            new_min_y = new_center_y - new_delta_y / 2.
            new_min_y = (new_min_y + 2.5) // 5 * 5
            new_min_y = min(graph.allowed_max_y - new_delta_y, new_min_y)
            new_min_y = max(graph.allowed_min_y, new_min_y)
            new_max_y = new_min_y + new_delta_y
            new_max_y = min(graph.allowed_max_y, new_max_y)
            graph.ymin = new_min_y
            graph.ymax = new_max_y
        else:
            self.begin_min_y = graph.ymin
            self.begin_max_y = graph.ymax
            # print('begin_min=' + str(self.begin_min_y) + ' _max=' + str(self.begin_max_y))
