# hotpot_km
 A library for a pooling hotloaded Jupyter kernels 

# Example usage with Voila

## Requirements

 * voila master (Fri 12 Mar 2021)

## Create an environment

```
$ mamba create -y -q -c conda-forge -n hotpot-km-test python=3.7 glueviz notebook scipy numpy matplotlib pip nodejs=12
$ conda activate hotpot-km-test
$ pip install "hotpot-km==0.1.*"
$ pip install git+https://github.com/spacetelescope/jdaviz/
$ pip install git+https://github.com/voila-dashboards/voila/ --force-reinstall
$ mkdir pooled
$ cd pooled
$ touch voila.json  # and fill with content below
$ touch ~/.jupyter/kernel_pool_init_python3.py  # and fill with content below
```

`voila.json`
```json
{
    "VoilaConfiguration": {
        "multi_kernel_manager_class": "hotpot_km.mapping.PooledMappingKernelManager"
    },
    "PooledKernelManager": {
        "kernel_pools": {
            "python3": 3
        },
        "_wait_at_startup": true
    }
}
```

`kernel_pool_init_python3.py`
```python
modules = {'imageio.core.request', 'glue.plugins.dendro_viewer.qt.options_widget', 'glue.dialogs.data_wizard', 'setuptools.extern.six', 'vispy.visuals.volume', 'echo.qt.connect', 'glue.viewers.histogram.qt', 'vispy.geometry.triangulation', 'vispy.util.keys', 'setuptools.py34compat', 'vispy.visuals.transforms.linear', 'glue_vispy_viewers.common.viewer_state', 'vispy.scene.visuals', 'glue.external.modest_image', 'glue_astronomy.io.spectral_cube.spectral_cube', 'vispy.visuals.shaders.compiler', 'vispy.ext.ipy_inputhook', 'glue_vispy_viewers.scatter.multi_scatter', 'glue.viewers.matplotlib.qt.compute_worker', 'vispy.scene.subscene', 'vispy.ext.six', 'vispy.ext._bundled.cassowary.utils', 'glue_vispy_viewers.common', 'distutils.filelist', 'ctypes.macholib.dyld', 'vispy.visuals.shaders.program', 'vispy.visuals.transforms.interactive', 'glue.viewers.histogram.compat', 'imageio.plugins.npz', 'vispy.visuals.regular_polygon', 'glue.viewers.profile.viewer', 'glue_vispy_viewers.common.selection_tools', 'glue.viewers.profile.qt.layer_style_editor', 'setuptools.extern.packaging', 'setuptools', 'glue.plugins.coordinate_helpers', 'vispy.visuals.plane', 'vispy.color.color_array', 'vispy.scene', 'vispy.ext._bundled.six.moves', 'vispy.scene.events', 'vispy.gloo.gl._gl2', 'vispy.visuals.graphs.layouts', 'glue_vispy_viewers.scatter.layer_state', 'PyQt5.uic.exceptions', 'vispy.gloo.program', 'setuptools.monkey', 'vispy.util.transforms', 'vispy.scene.cameras.magnify', 'PyQt5.uic.Compiler.proxy_metaclass', 'glue_vispy_viewers', 'imageio.plugins.pillow', 'glue.core.roi_pretransforms', 'glue.core.aggregate', 'vispy.app.canvas', 'vispy.util.fonts._triage', 'glue.utils.qt.mixins', 'vispy.visuals.mesh', 'glue.utils.qt.helpers', 'vispy.glsl', 'glue_vispy_viewers.scatter.scatter_viewer', 'echo.qt.autoconnect', 'glue.core.qt.fitters', 'PyQt5.uic.Compiler.indenter', 'setuptools.config', 'vispy.visuals.text._sdf_gpu', 'vispy.gloo.globject', 'glue_vispy_viewers.scatter.scatter_toolbar', 'vispy.visuals.shaders.expression', 'PyQt5.uic', 'vispy.app.backends', 'glue_vispy_viewers.scatter.viewer_state', 'qtpy.QtGui', 'vispy.visuals.colorbar', 'vispy.scene.cameras.fly', 'vispy.color._color_dict', 'matplotlib.backends.qt_editor', 'distutils.archive_util', 'glue.viewers.histogram.qt.options_widget', 'vispy.visuals.filters.clipper', 'setuptools.extern.packaging._compat', 'glue.viewers.matplotlib.viewer', 'glue._plugin_helpers', 'qtpy._patch.qheaderview', 'qtpy.py3compat', 'glue.dialogs.data_wizard.qt.data_wizard_dialog', 'vispy.util.fonts._quartz', 'PyQt5.uic.port_v3', 'distutils.dist', 'glue.plugins.dendro_viewer.compat', 'vispy.util.config', 'ctypes.macholib', 'vispy.ext._bundled.cassowary', 'glue_vispy_viewers.volume.shaders', 'setuptools.extern.six.moves', 'vispy.scene.widgets.label', 'glue.utils.qt.mime', 'glue.core.qt.dialogs', 'setuptools._vendor.packaging', 'vispy.app', 'glue.io.formats.fits.subset_mask', 'glue.utils.qt.app', 'vispy.app.application', 'PyQt5.QtGui', 'vispy.geometry.meshdata', 'glue.viewers.histogram.qt.layer_artist', 'vispy.visuals.isosurface', 'imageio.core.format', 'qtpy.QtCore', 'setuptools._vendor.six.moves', 'PyQt5.uic.properties', 'vispy.visuals.isoline', 'glue.viewers.profile.qt.options_widget', 'vispy.scene.widgets.console', 'glue.utils.qt.autocomplete_widget', 'glue.viewers.scatter.python_export', 'setuptools._vendor', 'vispy.util.dpi._quartz', 'glue.viewers.scatter.qt', 'imageio.plugins.ffmpeg', 'glue.plugins.dendro_viewer.qt.data_viewer', 'glue_vispy_viewers.common.toolbar', 'glue.viewers.common.qt.data_slice_widget', 'glue_vispy_viewers.volume.layer_style_widget', 'vispy.util.quaternion', 'imageio.plugins.pillow_info', 'vispy.util', 'vispy.visuals.shaders.multiprogram', 'setuptools.py33compat', 'vispy.visuals.line_plot', 'glue.viewers.histogram.qt.layer_style_editor', 'vispy.geometry.calculations', 'vispy.gloo.gl._constants', 'vispy.visuals.scrolling_lines', 'glue_vispy_viewers.scatter.layer_artist', 'vispy.gloo.gl._proxy', 'glue.plugins.dendro_viewer.dendro_helpers', 'setuptools._vendor.six', 'vispy.scene.cameras.turntable', 'html.parser', 'glue_vispy_viewers.common.vispy_widget', 'vispy.ext._bundled.cassowary.simplex_solver', 'setuptools._imp', 'vispy.ext._bundled.husl', 'vispy.app.timer', 'vispy.visuals.graphs.layouts.force_directed', 'glue.plugins.dendro_viewer.qt.layer_style_editor', 'vispy', '_distutils_hack', 'imageio.core', 'glue_vispy_viewers.common.layer_artist', 'glue.utils.qt.dialogs', 'matplotlib.backends.qt_compat', 'vispy.io.mesh', 'ctypes.util', 'PyQt5.uic.Compiler.qtproxies', 'glue.utils.qt.delegates', 'glue.plugins.tools.python_export', 'glue_vispy_viewers.volume.viewer_state', 'vispy.ext.cassowary', 'glue.viewers.scatter.viewer', 'imageio.plugins._freeimage', 'glue.viewers.histogram.qt.data_viewer', 'glue.viewers.profile.layer_artist', 'glue_vispy_viewers.volume.layer_state', 'glue.viewers.histogram', 'vispy.ext._bundled.cassowary.error', 'vispy.ext._bundled.png', 'matplotlib.backends.backend_qt5', 'vispy.util.dpi', 'vispy.ext._bundled.six', 'imageio.plugins.fits', 'vispy.visuals.graphs.layouts.random', 'vispy.visuals.shaders.shader_object', 'vispy.ext.six.moves', 'vispy.ext._bundled.six.moves.urllib', 'vispy.visuals.gridlines', 'vispy.visuals.shaders.parsing', 'glue.viewers.image.qt.slice_widget', 'PyQt5.uic.objcreator', 'glue.utils.qt.python_list_model', 'vispy.visuals.windbarb', 'imageio.plugins.freeimage', 'glue_vispy_viewers.volume.colors', 'glue.viewers.scatter.qt.options_widget', 'glue.viewers.matplotlib.qt', 'PyQt5.uic.icon_cache', 'glue_vispy_viewers.common.layer_state', 'glue.core.simpleforms', 'vispy.visuals.graphs.util', 'setuptools.extern.packaging._structures', 'vispy.util.eq', 'glue_vispy_viewers.compat.text', 'glue.viewers.profile.qt.mouse_mode', 'glue_vispy_viewers.common.tools', 'imageio.plugins.swf', 'vispy.util.bunch', 'glue.plugins.dendro_viewer.state', 'vispy.ext._bundled.cassowary.expression', 'glue_vispy_viewers.volume.volume_visual', 'glue.viewers.image.qt.layer_style_editor_subset', 'vispy.visuals.visual', 'matplotlib.backends.qt_editor._formsubplottool', 'vispy.scene.cameras.base_camera', '_distutils_hack.override', 'glue.plugins.dendro_viewer.qt', 'glue_vispy_viewers.common.axes', 'glue.viewers.image.qt.profile_viewer_tool', 'glue.viewers.table', 'setuptools.extension', 'vispy.visuals.text.text', 'vispy.util.fonts._vispy_fonts', 'vispy.util.fetching', 'vispy.color.color_space', 'vispy.visuals.graphs.graph', 'vispy.scene.cameras.arcball', 'vispy.geometry', 'setuptools.version', 'vispy.visuals.shaders.variable', 'vispy.visuals.spectrogram', 'vispy.visuals.surface_plot', 'vispy.app.inputhook', 'imageio.core.util', 'imageio.plugins.example', 'glue.viewers.matplotlib.qt.toolbar', 'glue.viewers.image.viewer', 'glue.viewers.image.qt.layer_style_editor', 'vispy.gloo.gl', 'vispy.visuals.sphere', 'matplotlib.backends.qt_editor._formlayout', 'imageio.plugins.dicom', 'PyQt5.QtWidgets', 'vispy.ext.png', 'glue_vispy_viewers.volume', 'glue.viewers.table.qt.data_viewer', '_markupbase', 'glue.dialogs', 'vispy.app.base', 'glue.viewers.scatter.compat', 'vispy.scene.canvas', 'glue.utils.qt.decorators', 'vispy.io.wavefront', 'glue.io.formats.fits', 'setuptools._vendor.ordered_set', 'vispy.visuals.rectangle', 'imageio.plugins.bsdf', 'vispy.visuals.shaders.function', 'imageio.plugins.grab', 'qtpy.compat', 'vispy.visuals.polygon', 'glue.plugins.dendro_viewer', 'glue.viewers.matplotlib.qt.widget', 'vispy.scene.cameras.panzoom', 'setuptools._deprecation_warning', 'setuptools.py27compat', 'glue.core.data_exporters.hdf5', 'vispy.geometry.rect', 'vispy.ext.gzip_open', 'vispy.util.ptime', 'vispy.io.stl', 'vispy.scene.cameras', 'vispy.color', 'vispy.visuals.transforms', 'vispy.visuals.transforms.chain', 'glue.viewers.common.qt.data_viewer', 'setuptools._vendor.packaging.__about__', 'vispy.visuals.axis', 'vispy.gloo.preprocessor', 'vispy.scene.widgets.grid', 'PyQt5.uic.Compiler.compiler', 'vispy.scene.node', 'glue.core.data_exporters', 'glue.core.qt.style_dialog', 'glue.core.qt.mime', 'imageio.core.fetching', 'glue.plugins.dendro_viewer.layer_artist', 'sip', 'vispy.visuals.image', 'vispy.visuals.transforms.transform_system', 'glue.viewers.image.qt.options_widget', 'glue.icons.qt', 'glue.viewers.histogram.state', 'vispy.visuals.text', 'glue.viewers.scatter.qt.data_viewer', 'imageio.core.functions', 'vispy.color.colormap', 'qtpy.QtWidgets', 'glue.core.data_exporters.astropy_table', 'glue.viewers.matplotlib.qt.toolbar_mode', 'vispy.ipython', 'vispy.app._default_app', 'vispy.util.logs', 'PyQt5.uic.Compiler.qobjectcreator', 'vispy.gloo.wrappers', 'imageio.plugins.tifffile', 'glue.viewers.matplotlib.mpl_axes', 'matplotlib.backends.backend_qt5agg', 'vispy.visuals.ellipse', 'imageio.plugins', 'vispy.visuals.cube', 'glue.io.qt', 'vispy.geometry.polygon', 'glue.core.qt', 'vispy.ext._bundled.decorator', 'vispy.visuals.tube', 'PyQt5.uic.uiparser', 'distutils.extension', 'glue.viewers.image.qt.standalone_image_viewer', 'vispy.visuals.infinite_line', 'PyQt5', 'vispy.geometry.isocurve', 'vispy.visuals.graphs.layouts.circular', 'vispy.ext.cocoapy', 'vispy.util.wrappers', 'glue_vispy_viewers.utils', 'setuptools.depends', 'vispy.ext.decorator', 'qtpy._patch.qcombobox', 'glue.plugins.tools.pv_slicer.qt', 'imageio.core.findlib', 'vispy.visuals', 'glue.viewers.scatter.qt.layer_style_editor', 'setuptools.extern.ordered_set', 'vispy.version', 'vispy.geometry.isosurface', 'vispy.visuals.markers', 'vispy.visuals.filters.color', 'vispy.gloo.util', 'vispy.geometry.torusknot', 'glue.viewers.common.qt.toolbar', 'glue_vispy_viewers.scatter', 'PyQt5.uic.port_v3.ascii_upper', 'glue.viewers.image.qt.mouse_mode', 'vispy.visuals.linear_region', 'glue.utils.qt', 'vispy.scene.widgets.widget', 'glue.viewers.scatter.layer_artist', 'vispy.visuals.transforms._util', 'vispy.ext._bundled', 'vispy.util.fourier', 'glue.utils.qt.colors', 'glue.plugins.export_d3po', 'vispy.visuals.transforms.base_transform', 'glue.viewers.profile.qt.profile_tools', 'vispy.ipython.ipython', 'vispy.visuals.graphs', 'vispy.visuals.isocurve', 'distutils.config', 'glue.viewers.image.qt', 'setuptools.extern.packaging.version', 'glue.viewers.histogram.viewer', 'qtpy._version', 'vispy.gloo.context', 'glue_vispy_viewers.compat.axis', 'imageio.plugins.simpleitk', 'glue.plugins.tools', 'vispy.visuals.xyz_axis', 'vispy.visuals.gridmesh', 'vispy.ext.cubehelix', 'qtpy.uic', 'glue.viewers.matplotlib.qt.data_viewer', 'vispy.visuals.line.line', 'PyQt5.uic.Compiler.misc', 'glue.plugins.tools.pv_slicer', 'OpenGL.version', 'vispy.visuals.line.dash_atlas', 'glue.core.data_exporters.gridded_fits', 'glue.icons.qt.helpers', 'vispy.gloo.buffer', 'glue.core.qt.simpleforms', 'glue.viewers.profile.qt.data_viewer', 'glue_vispy_viewers.volume.layer_artist', 'OpenGL', 'vispy.scene.cameras.perspective', 'PyQt5.uic.Compiler', 'vispy.visuals.line.arrow', 'PyQt5.QtCore', 'glue.plugins.wcs_autolinking', 'qtpy', 'glue_vispy_viewers.common.compat', 'vispy.visuals.histogram', 'glue.viewers.image.qt.data_viewer', 'vispy.scene.widgets.axis', 'vispy.io.datasets', 'glue.core.qt.layer_artist_model', 'glue.viewers.common.qt', 'distutils.cmd', 'vispy.gloo.glir', 'glue.io', 'glue_vispy_viewers.volume.volume_toolbar', 'vispy.visuals.shaders', 'setuptools.extern', 'glue.plugins.tools.pv_slicer.qt.pv_slicer', 'glue.viewers.common.qt.base_widget', 'vispy.gloo.gl.gl2', 'setuptools.extern.packaging.utils', 'imageio.plugins.pillowmulti', 'glue_astronomy.io', 'vispy.util.event', 'vispy.util.profiler', 'glue.viewers.histogram.layer_artist', 'glue.viewers.profile.qt.layer_artist', 'glue.viewers.image.compat', 'PyQt5.uic.port_v3.as_string', 'vispy.io.image', 'vispy.visuals.line', 'PyQt5.uic.port_v3.proxy_base', 'vispy.io', 'glue.viewers.common.qt.data_viewer_with_state', 'setuptools.msvc', 'vispy.visuals.filters', 'imageio.plugins.spe', 'glue.utils.noconflict', 'imageio.plugins.feisem', 'vispy.ext.husl', 'glue.io.formats', 'imageio.plugins.freeimagemulti', 'glue.plugins.wcs_autolinking.wcs_autolinking', 'vispy.visuals.text._sdf_cpu', 'glue.external.echo.qt', 'vispy.geometry.generation', 'vispy.scene.widgets.viewbox', 'qtpy._patch', 'glue.viewers.profile.qt', 'glue.viewers.image.qt.pixel_selection_mode', 'vispy.scene.cameras._base', 'ctypes.macholib.framework', 'vispy.visuals.filters.base_filter', 'glue_vispy_viewers.common.viewer_options', 'OpenGL.plugins', 'distutils.core', 'setuptools.extern.packaging._typing', 'imageio', 'glue.viewers.table.compat', 'vispy.ext', 'glue.viewers.histogram.python_export', 'glue.io.qt.directory_importer', 'echo.qt', 'PyQt5.sip', 'vispy.ext._bundled.cassowary.tableau', 'imageio.plugins.lytro', 'setuptools.dist', 'glue_vispy_viewers.common.vispy_data_viewer', 'vispy.ext._bundled.cassowary.edit_info', 'glue_vispy_viewers.compat', 'glue.viewers.image.qt.contrast_mouse_mode', 'vispy.util.check_environment', 'vispy.scene.widgets', 'glue.io.qt.directory_importer.directory_importer', 'glue_astronomy.io.spectral_cube', 'vispy.visuals.border', 'glue.utils.qt.widget_properties', 'vispy.scene.widgets.colorbar', 'setuptools.extern.packaging.specifiers', 'setuptools.windows_support', 'imageio.plugins.gdal', 'vispy.gloo.framebuffer', 'vispy.visuals.box', 'vispy.util.frozen', 'vispy.visuals.transforms.nonlinear', 'ctypes.macholib.dylib', 'matplotlib.backends.qt_editor.figureoptions', 'vispy.util.fonts', 'vispy.gloo.texture', 'glue.plugins.coordinate_helpers.link_helpers', 'vispy.gloo', 'distutils.fancy_getopt', 'vispy.visuals.filters.picking', 'glue_vispy_viewers.scatter.layer_style_widget', 'glue.viewers.profile.python_export', 'glue.utils.qt.threading', 'glue.dialogs.data_wizard.qt', 'glue.viewers.table.qt', 'glue_vispy_viewers.volume.volume_viewer'}

import importlib
for mod in modules:
    if not mod.startswith("setuptools"):
        importlib.import_module(mod)
```

Create a notebook (test.ipynb) with 1 cell:
```bash
from jdaviz.app import Application
app = Application(configuration='cubeviz')
display(app)
```

Run voila (from the directory with voila.json)
```bash
$ voila --no-browser test.ipynb
```

From another terminal:
```bash
$ time curl http://localhost:8866/ > /dev/null
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 12212    0 12212    0     0   6478      0 --:--:--  0:00:01 --:--:--  6478
curl http://localhost:8866/ > /dev/null  0.01s user 0.01s system 0% cpu 1.895 total
```

We see this runs in less then 2 seconds.

Now if we start voila from another directory (to disable the kernel pool)

From another terminal:
```bash
$ time curl http://localhost:8866/ > /dev/null
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 12212    0 12212    0     0   1751      0 --:--:--  0:00:06 --:--:--   386
0.01s user 0.01s system 0% cpu 6.990 total
```

We see it takes between 6 and 7 seconds.