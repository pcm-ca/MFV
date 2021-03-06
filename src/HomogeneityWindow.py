import sys

is_frozen = getattr(sys, 'frozen', False)
frozen_temp_path = getattr(sys, '_MEIPASS', '')

import os

# This is needed to find resources when using pyinstaller
if is_frozen:
    basedir = frozen_temp_path
else:
    basedir = os.path.dirname(os.path.abspath(__file__))
resource_dir = os.path.join(basedir, 'resources')




import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

from matplotlib import pyplot
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
# from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3 as NavigationToolbar

from PlotWindow import PlotBox
from functions import uniformity, compute_norm
from About import AboutWindow
from ErrorMessage import ErrorMessage
import numpy

class HomogeneityWindow():
    def __init__(self, parent, simulation, colormap, zoom_value=0, homogeneity=0.0):
        self.zoom = 100.0
        self.homo = 97.0

        self.parent = parent
        self.simulation = simulation
        self.colormap = colormap
        self.zoom_value = zoom_value
        self.homogeneity = homogeneity

        
        self.builder = Gtk.Builder()
        self.builder.add_from_file(resource_dir + "/homogeneity.glade")
        self.window = self.builder.get_object("wndHomo")
        self.statBar = self.builder.get_object("statBar")
        self.btnApplyHomo = self.builder.get_object("btnApplyHomo")
        self.btnApplyZoom = self.builder.get_object("btnApplyZoom")
        self.txtZoomValue = self.builder.get_object("txtZoomValue")
        self.txtHomoValue = self.builder.get_object("txtHomoValue")
        self.boxPlot = self.builder.get_object("boxPlot")
        self.menuColorMap = self.builder.get_object("menuColorMap")
        self.btnQuit = self.builder.get_object("btnQuit")
        self.btnAbout = self.builder.get_object("btnAbout")
        self.txtExperimentationVolume = self.builder.get_object("txtExperimentationVolume")


        self.window.set_transient_for(self.parent.window)

        self.txtZoomValue.connect("key-press-event", self.on_key_press_event_zoom)
        self.txtHomoValue.connect("key-press-event", self.on_key_press_event_homo)


        self.btnApplyZoom.connect("clicked", self.on_apply_zoom)
        self.btnApplyHomo.connect("clicked", self.on_apply_homo)
        self.btnQuit.connect("activate", lambda _: self.window.close())
        self.btnAbout.connect("activate", lambda _: AboutWindow(self.window))

        self.plot = PlotBox(self, self.simulation, self.colormap, self.statBar, binary_colors=True)
        
        self.boxPlot.pack_start(self.plot.boxPlot, True, True, 0)


        # Get a list of the colormaps in matplotlib.  Ignore the ones that end with
        # '_r' because these are simply reversed versions of ones that don't end
        # with '_r'
        maps = sorted(m for m in pyplot.cm.datad if not m.endswith("_r"))

        firstitem = Gtk.RadioMenuItem(self.colormap)
        firstitem.set_active(True)
        firstitem.connect('activate', self.on_color_bar_menu, self.colormap)
        self.menuColorMap.append(firstitem)
        for name in maps:
            if name != self.colormap:
                item = Gtk.RadioMenuItem.new_with_label([firstitem], name)
                item.set_active(False)
                item.connect('activate', self.on_color_bar_menu, name)
                self.menuColorMap.append(item)



        self.txtZoomValue.set_text(str(self.zoom))
        self.txtHomoValue.set_text(str(self.homo))
        self.btnApplyHomo.emit("clicked")

        self.plot.boxLimits.hide()
        
        self.window.show_all()
        
        self.plot.txtMinLimit.hide()
        self.plot.txtMaxLimit.hide()
        self.plot.lblBmin.hide()
        self.plot.lblBmax.hide()
        self.plot.btnApplyLimits.hide()

    def on_key_press_event_zoom(self, widget, event):


        # check the event modifiers (can also use SHIFTMASK, etc)
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)

        # see if we recognise a keypress
        if Gdk.keyval_name(event.keyval) == 'Return':
            self.on_apply_zoom(None)

    def on_key_press_event_homo(self, widget, event):

        # check the event modifiers (can also use SHIFTMASK, etc)
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)

        # see if we recognise a keypress
        if Gdk.keyval_name(event.keyval) == 'Return':
            self.on_apply_homo(None)

    def isNumeric(self, val, func=float):
        try:
            func(val)
            return True
        except Exception as e:
            return False

    def on_apply_zoom(self, widget):
        self.plot.rect = None
        value = self.txtZoomValue.get_text().replace("%", "")
        self.zoom = float(value) if self.isNumeric(value) else False

        if not (self.zoom and self.zoom > 0):
            ErrorMessage(self.window, "Invalid input parameters", "Zoom value must be a positive real.")
            return

        zmin, zmax, ymin, ymax = self.plot.compute_zoom(self.zoom)

        self.parent.plot.draw_rectangle(zmin, zmax, ymin, ymax)
        self.txtZoomValue.set_text("{}%".format(self.zoom))

        self.plot_rectangle_homo()



    def on_apply_homo(self, widget):
        self.plot.rect = None
        value = self.txtHomoValue.get_text().replace("%", "")
        self.homo = float(value) if self.isNumeric(value) else False

        if not (self.homo and self.homo > 0 and self.homo <= 100):
            ErrorMessage(self.window, "Invalid input parameters", "Homogeneity value must be a positive real lower than 100.")
            return


        self.txtZoomValue.set_text("100.0%")
        
        value = self.txtZoomValue.get_text().replace("%", "")
        self.zoom = float(value) if self.isNumeric(value) else False

        if not (self.zoom and self.zoom > 0):
            ErrorMessage(self.window, "Invalid input parameters", "Zoom value must be a positive real.")
            return

        center, uniformity_grid = self.compute_uniformity()
        homo_grid = numpy.where(uniformity_grid >= (self.homo / 100), 1, 0)


        self.plot.initial_norm = homo_grid.copy()
        zmin, zmax, ymin, ymax = self.plot.compute_zoom(self.zoom)

        self.mid = self.compute_max_square(center)
        self.plot_rectangle_homo()

        self.parent.plot.draw_rectangle(zmin, zmax, ymin, ymax)
        self.txtHomoValue.set_text("{}%".format(self.homo))
        self.txtZoomValue.set_text("{}%".format(self.zoom))

        self.center = center

        self.write_experimentation_values()



    def compute_uniformity(self):
        zmid = (self.simulation.z_max + self.simulation.z_min) * 0.5
        ymid = (self.simulation.y_max + self.simulation.y_min) * 0.5
        center = (zmid, ymid)
        return center, uniformity(
            self.simulation.coils, self.simulation.norm, self.simulation.mu0, center)

    def on_color_bar_menu(self, widget, name):
        self.colormap = name
        self.plot.update_plot(name)


    def compute_max_square(self, center):
        low = 0.0
        high = max([abs(self.simulation.z_min), abs(self.simulation.z_max), abs(self.simulation.y_min), abs(self.simulation.y_max)])
        mid = (low + high) * 0.5

        p = 20
        ones = numpy.ones(p)
        while abs(high - low) > 1e-5:
            line = numpy.linspace(-mid, mid, p)
            line = numpy.linspace(-mid, mid, p)
            down = numpy.array([line, - mid * ones]).T
            up = numpy.array([line, mid * ones]).T
            left = numpy.array([- mid * ones, line]).T
            rigth = numpy.array([mid * ones, line]).T
            points = numpy.concatenate((up, down, left, rigth), axis=0)
            
            decrease = False
            for z, y in points:
                val = compute_norm(self.simulation.coils, abs(y), z, self.simulation.mu0)
                u = uniformity(self.simulation.coils, numpy.array([val]), self.simulation.mu0, center)[0]
                if u < (self.homo / 100):
                    decrease = True
                    break

            if decrease:
                high = mid
            else:
                low = mid
            mid = (low + high) * 0.5
            
        return mid


    def plot_rectangle_homo(self):
        self.homo_zmin = max([self.simulation.z_min, -self.mid])
        self.homo_zmax = min([self.simulation.z_max, self.mid])
        self.homo_ymin = max([self.simulation.y_min, -self.mid])
        self.homo_ymax = min([self.simulation.y_max, self.mid])



        self.homo_width = self.homo_zmax - self.homo_zmin 
        self.homo_height = self.homo_ymax - self.homo_ymin
        self.plot.draw_rectangle(
            self.homo_zmin,
            self.homo_zmax,
            self.homo_ymin,
            self.homo_ymax)





    def write_experimentation_values(self):
        if numpy.sign(self.homo_ymax) == numpy.sign(self.homo_ymin):
            r2 = max([abs(self.homo_ymax), abs(self.homo_ymin)])
            r1 = min([abs(self.homo_ymax), abs(self.homo_ymin)])
        else:
            r2 = max([abs(self.homo_ymax), abs(self.homo_ymin)])
            r1 = 0

        volume = numpy.pi * self.homo_width * (r2 ** 2 - r1 ** 2)

        Bo = compute_norm(self.simulation.coils, *self.center, self.simulation.mu0)


        text = "\n"
        text += " \t{}\n".format("Dimensions:")
        text += "\n"
        text += " \t\t{}\t\t\t=\t\t{:.5f}\n".format("Height [m]", self.homo_width)
        text += " \t\t{}\t\t\t=\t\t{:.5f}\n".format("Width [m]", self.homo_height)
        text += " \t\t{}\t\t\t=\t\t{:.5f}\n".format("Volume [m³]", volume)
        text += "\n"
        text += " \t{}\n".format("Magnetic field value at the center of the volume:")
        text += "\n"
        text += " \t\t{}\t\t\t\t\t\t=\t\t{:.5f}\n".format("Bo [mT]", Bo)
        text += " \t\t{}\t\t=\t\t(z = {:.5f}, y = {:.5f})\n".format("Center coordinates [m]", *self.center)

        self.txtExperimentationVolume.get_buffer().set_text(text)
