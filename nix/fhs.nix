{ pkgs, runScript ? "bash" }:

# An FHS-style sandbox containing every system library PsychoPy's binary
# wheels (psychopy, wxpython, pyo, soundfile, ffmpeg-python, glfw, …) expect to
# find at the usual /usr/lib + /lib64 paths on a normal-Linux distribution.
#
# We use this instead of LD_LIBRARY_PATH gymnastics because:
#   1. Nothing inside the wheel is patchelf'd.
#   2. dlopen() lookups resolve correctly (wxPython does many at runtime).
#   3. The same env works identically on Saturn / Jupiter / Mercury / Moon.
#
# A venv is created inside this env on first run (see launcher.nix).

pkgs.buildFHSEnv {
  name = "psychopy-fhs";

  targetPkgs = p: with p; [
    # ── Toolchain & python ──────────────────────────────────────────────
    # python3.11 -m venv (stdlib + ensurepip) installs pip into the venv
    # itself; no need to pull python311.pkgs.{pip,virtualenv} into the FHS
    # env (they currently drag sphinx 9.x which only supports py >= 3.12).
    python311
    uv
    pkg-config
    gcc
    gnumake
    git
    cacert
    bashInteractive
    coreutils
    findutils
    gnused
    gnugrep
    which

    # ── X11 / display ───────────────────────────────────────────────────
    libx11
    libxext
    libxrender
    libxinerama
    libxi
    libxrandr
    libxcursor
    libxcomposite
    libxdamage
    libxfixes
    libxcb
    libsm
    libice
    libxtst
    libxxf86vm
    libxkbcommon
    curl
    pcre2

    # ── OpenGL ──────────────────────────────────────────────────────────
    libGL
    libGLU
    mesa

    # ── GTK + wx + webview ──────────────────────────────────────────────
    gtk3
    glib
    cairo
    pango
    gdk-pixbuf
    atk
    libepoxy
    webkitgtk_4_1
    wxwidgets_3_2
    libnotify

    # ── Multimedia ──────────────────────────────────────────────────────
    portaudio
    libsndfile
    ffmpeg
    SDL2
    gst_all_1.gstreamer
    gst_all_1.gst-plugins-base
    gst_all_1.gst-plugins-good
    alsa-lib

    # ── Lab Streaming Layer ────────────────────────────────────────────
    liblsl

    # ── Common image / font deps ───────────────────────────────────────
    zlib
    # The wxPython Linux wheel (built on Ubuntu 22.04) links against
    # libjpeg.so.8; nixpkgs.libjpeg is libjpeg-turbo with soname .62, so
    # libjpeg8 is needed too.
    libjpeg
    libjpeg8
    libpng
    libtiff
    expat
    freetype
    fontconfig
    dbus
  ];

  multiPkgs = p: with p; [ stdenv.cc.cc ];

  inherit runScript;

  profile = ''
    # PsychoPy's audio backends look for these.
    export ALSA_PLUGIN_DIR=${pkgs.alsa-plugins}/lib/alsa-lib

    # pip + uv inside the FHS env should use the same TLS bundle as nix.
    export SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
    export NIX_SSL_CERT_FILE=$SSL_CERT_FILE

    # Plasma (and GNOME) set GTK_MODULES / GTK_PATH pointing at
    # /run/current-system/sw/lib/gtk-3.0/modules so e.g. appmenu-gtk-module
    # and colorreload-gtk-module load globally. Those .so's are linked
    # against the host's GTK, NOT the GTK we ship in this FHS env, so they
    # surface as `undefined symbol: gtk_module_display_init` and (on a
    # live Wayland session) prevent the wxPython app from realising any
    # window. Clear them so GTK falls back to the FHS env's own modules.
    unset GTK_MODULES GTK3_MODULES GTK_PATH GTK3_PATH GTK_IM_MODULE_FILE

    # Same reasoning for QT plugin paths — we don't use Qt here, but
    # wxPython links libsoup/webkit which transitively peek at these.
    unset QT_PLUGIN_PATH QML2_IMPORT_PATH

    # Keep the venv discoverable to the launcher.
    : "''${PSYCHOPY_FLAKE_REQS:=missing}"
  '';
}
