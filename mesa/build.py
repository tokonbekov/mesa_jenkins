 #!/usr/bin/python

import os
import sys
import os.path as path
sys.path.append(path.join(path.dirname(path.abspath(sys.argv[0])), ".."))
import build_support as bs


class MesaBuilder(bs.AutoBuilder):
    """Provides mesa-specific customizations to AutoBuilder"""
    def __init__(self):
        global_opts = bs.Options()

        options = []
        if global_opts.arch == "m32":
            # expat pkg-config fails for some reason on i386
            options = ['EXPAT_LIBS="-L/usr/lib/i386-linux-gnu -lexpat"']

        surfaceless = ""
        if path.exists(bs.ProjectMap().project_source_dir() + "/src/egl/drivers/dri2/platform_surfaceless.c"):
            # surfaceless not supported on 10.6 and earlier
            surfaceless = ",surfaceless"

        options = options + ["--enable-gbm",
                             "--with-egl-platforms=x11,drm" + surfaceless,
                             "--enable-glx-tls", 
                             "--enable-gles1",
                             "--enable-gles2",
                             "--with-dri-drivers=i965,swrast,i915",

                             # disable video drivers:
                             # bbe6f7f865cd4316b5f885507ee0b128a20686eb
                             # caused build failure unrelated to intel mesa
                             # team.
                             "--disable-xvmc",
                             "--disable-vdpau",

                             # gallium tested with mesa-buildtest
                             "--without-gallium-drivers"]
        if os.path.exists(bs.ProjectMap().project_source_dir() + "/src/intel/vulkan"):
            options.append("--with-vulkan-drivers=intel")

        if global_opts.config == 'debug':
            options.append('--enable-debug')

        # always enable optimizations in mesa because tests are too slow
        # without them.
        bs.AutoBuilder.__init__(self, configure_options=options, opt_flags="-O2")

    def build(self):
        """since mesa doesn't install an icd, generate one"""
        bs.AutoBuilder.build(self)
        icd_path = "/tmp/build_root/" + self._options.arch + "/usr/share/vulkan/icd.d/dev_icd.json"
        icd_content = """\
{
    "file_format_version": "1.0.0",
    "ICD": {
        "library_path": "/tmp/build_root/%s/lib/libvulkan_intel.so",
        "abi_versions": "1.0.3"
    }
}
""" % self._options.arch
        if not os.path.exists(os.path.dirname(icd_path)):
            os.makedirs(os.path.dirname(icd_path))
        with open(icd_path, "w") as icd_f:
            icd_f.write(icd_content)

    def test(self):
        """Provide gtests as available"""
        # override the test method, because tests have moved
        gtests = ["src/glx/tests/glx-test",
                  "src/mesa/main/tests/main-test",
                  "./src/mapi/shared-glapi-test",
                  "src/compiler/glsl/tests/general-ir-test",
                  "src/compiler/glsl/tests/sampler-types-test",
                  "src/compiler/glsl/tests/uniform-initializer-test"]

        if path.exists(self._src_dir + "/src/intel/compiler/test_vec4_copy_propagation.cpp"):
            gtests += ["src/intel/compiler/test_vec4_copy_propagation",
                       "src/intel/compiler/test_vec4_register_coalesce"]
        self.SetGtests(gtests)
        bs.AutoBuilder.test(self)

bs.build(MesaBuilder())
