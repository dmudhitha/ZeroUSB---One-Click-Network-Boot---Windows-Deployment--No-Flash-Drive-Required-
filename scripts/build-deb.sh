#!/usr/bin/env bash
# ==============================================================================
# Script: build-deb.sh
# Purpose: Build a production Debian package (.deb) for ZeroUSB targeting /opt/zerousb
# ==============================================================================

set -euo pipefail

VERSION="${1:-1.2.0}"
ARCH="amd64"
PKG_NAME="zerousb"
DEB_NAME="${PKG_NAME}_${VERSION}_${ARCH}.deb"

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${SOURCE_DIR}/dist"
BUILD_ROOT="/tmp/zerousb_deb_build_${VERSION}"

echo "================================================================="
echo "   Building Debian Package: ${DEB_NAME} (Target: /opt/zerousb)   "
echo "================================================================="

# Clean build directory
rm -rf "${BUILD_ROOT}"
mkdir -p "${BUILD_ROOT}/DEBIAN"
mkdir -p "${BUILD_ROOT}/opt/zerousb"
mkdir -p "${BUILD_ROOT}/usr/bin"
mkdir -p "${BUILD_ROOT}/usr/share/applications"
mkdir -p "${BUILD_ROOT}/usr/share/pixmaps"
mkdir -p "${BUILD_ROOT}/usr/share/polkit-1/actions"
mkdir -p "${DIST_DIR}"

# 1. Copy Application files into /opt/zerousb
echo "[+] Staging application files to /opt/zerousb..."
cp "${SOURCE_DIR}/app.py" "${BUILD_ROOT}/opt/zerousb/"
cp "${SOURCE_DIR}/run-gui.sh" "${BUILD_ROOT}/opt/zerousb/"
cp "${SOURCE_DIR}/requirements.txt" "${BUILD_ROOT}/opt/zerousb/"
cp "${SOURCE_DIR}/README.md" "${BUILD_ROOT}/opt/zerousb/"

cp -r "${SOURCE_DIR}/ui" "${BUILD_ROOT}/opt/zerousb/"
cp -r "${SOURCE_DIR}/backend" "${BUILD_ROOT}/opt/zerousb/"
cp -r "${SOURCE_DIR}/config" "${BUILD_ROOT}/opt/zerousb/"
cp -r "${SOURCE_DIR}/scripts" "${BUILD_ROOT}/opt/zerousb/"
cp -r "${SOURCE_DIR}/assets" "${BUILD_ROOT}/opt/zerousb/"

# Clean cache directories from staging
find "${BUILD_ROOT}/opt/zerousb" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_ROOT}/opt/zerousb" -type f -name "*.pyc" -delete 2>/dev/null || true

# 2. Stage srv directory structure & core bootloader files
echo "[+] Staging PXE & bootloader assets into /opt/zerousb/srv..."
mkdir -p "${BUILD_ROOT}/opt/zerousb/srv/tftp"
mkdir -p "${BUILD_ROOT}/opt/zerousb/srv/http/boot"
mkdir -p "${BUILD_ROOT}/opt/zerousb/srv/http/images"
mkdir -p "${BUILD_ROOT}/opt/zerousb/srv/samba"

# Copy TFTP bootloaders (ipxe.efi, undionly.kpxe, memdisk)
for f in ipxe.efi undionly.kpxe memdisk boot.ipxe; do
    if [ -f "${SOURCE_DIR}/srv/tftp/${f}" ]; then
        cp -v "${SOURCE_DIR}/srv/tftp/${f}" "${BUILD_ROOT}/opt/zerousb/srv/tftp/"
    fi
done

# Copy HTTP bootloaders (wimboot, BCD, boot.sdi, etc.)
for f in wimboot wimboot.x86_64 memdisk boot.ipxe BCD boot.sdi bootmgr bootmgr.efi; do
    if [ -f "${SOURCE_DIR}/srv/http/boot/${f}" ]; then
        cp -v "${SOURCE_DIR}/srv/http/boot/${f}" "${BUILD_ROOT}/opt/zerousb/srv/http/boot/"
    fi
done

# Create lowercase bcd symlink for wimboot
cd "${BUILD_ROOT}/opt/zerousb/srv/http/boot" && ln -sf BCD bcd 2>/dev/null || true
cd "${SOURCE_DIR}"

if [ -f "${SOURCE_DIR}/srv/http/boot.ipxe" ]; then
    cp -v "${SOURCE_DIR}/srv/http/boot.ipxe" "${BUILD_ROOT}/opt/zerousb/srv/http/"
fi

# 3. Create /usr/bin/zerousb launcher wrapper
echo "[+] Creating /usr/bin/zerousb CLI & GUI launcher..."
cat << 'EOF' > "${BUILD_ROOT}/usr/bin/zerousb"
#!/usr/bin/env bash
exec /opt/zerousb/run-gui.sh "$@"
EOF
chmod +x "${BUILD_ROOT}/usr/bin/zerousb"

# 4. Install Desktop file and App Icon
echo "[+] Installing desktop integration & icon..."
cp "${SOURCE_DIR}/assets/zerousb.desktop" "${BUILD_ROOT}/usr/share/applications/"
cp "${SOURCE_DIR}/assets/icon.png" "${BUILD_ROOT}/usr/share/pixmaps/zerousb.png"
if [ -f "${SOURCE_DIR}/assets/org.zerousb.policy" ]; then
    cp "${SOURCE_DIR}/assets/org.zerousb.policy" "${BUILD_ROOT}/usr/share/polkit-1/actions/"
fi

# 5. Calculate Installed-Size in KB
INSTALLED_SIZE=$(du -sk "${BUILD_ROOT}" | awk '{print $1}')

# 6. Create DEBIAN/control
echo "[+] Writing DEBIAN/control metadata..."
cat << EOF > "${BUILD_ROOT}/DEBIAN/control"
Package: ${PKG_NAME}
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: ZeroUSB Team <https://github.com/dmudhitha/ZeroUSB>
Installed-Size: ${INSTALLED_SIZE}
Depends: python3 (>= 3.8), python3-tk, python3-pip, python3-pil, python3-pil.imagetk, dnsmasq, samba, wimtools, 7zip | p7zip-full, curl, iproute2, procps
Recommends: polkitd | policykit-1
Section: utils
Priority: optional
Homepage: https://github.com/dmudhitha/ZeroUSB
Description: One-Click Network Boot & High-Speed Multi-OS Deployment Platform
 ZeroUSB turns any Linux machine into an automated PXE deployment server.
 Deploy Windows 7, 8, 10, 11 and Linux distributions over local Ethernet
 at wire speed without USB flash drives, DVDs, or Windows Server WDS.
EOF

# 7. Create DEBIAN/postinst
echo "[+] Writing DEBIAN/postinst script..."
cat << 'EOF' > "${BUILD_ROOT}/DEBIAN/postinst"
#!/bin/bash
set -e

# Permissions for /opt/zerousb runtime directories
chmod -R 777 /opt/zerousb/srv 2>/dev/null || true
chmod -R 777 /opt/zerousb/config 2>/dev/null || true
chmod +x /opt/zerousb/run-gui.sh
chmod +x /opt/zerousb/scripts/*.sh 2>/dev/null || true
chmod +x /usr/bin/zerousb

# Ensure Python requirements are met
if command -v pip3 &>/dev/null; then
    pip3 install customtkinter psutil pillow --break-system-packages 2>/dev/null || \
    pip3 install customtkinter psutil pillow 2>/dev/null || true
fi

# Update desktop and icon caches
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database -q /usr/share/applications 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
fi

echo ""
echo "================================================================="
echo "  ⚡ ZeroUSB Multi-OS Deployment Server Installed Successfully! "
echo "  Target Directory: /opt/zerousb"
echo "  Command:          zerousb"
echo "  Desktop Launcher: Applications > System / Utility > ZeroUSB"
echo "================================================================="
echo ""

exit 0
EOF
chmod 755 "${BUILD_ROOT}/DEBIAN/postinst"

# 8. Create DEBIAN/prerm
echo "[+] Writing DEBIAN/prerm script..."
cat << 'EOF' > "${BUILD_ROOT}/DEBIAN/prerm"
#!/bin/bash
set -e

pkill -f "python3.*/opt/zerousb/app.py" 2>/dev/null || true
pkill -f "dnsmasq_gui_runtime.conf" 2>/dev/null || true

exit 0
EOF
chmod 755 "${BUILD_ROOT}/DEBIAN/prerm"

# 9. Create DEBIAN/postrm
echo "[+] Writing DEBIAN/postrm script..."
cat << 'EOF' > "${BUILD_ROOT}/DEBIAN/postrm"
#!/bin/bash
set -e

if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    rm -f /usr/bin/zerousb
    rm -f /usr/share/applications/zerousb.desktop
    rm -f /usr/share/pixmaps/zerousb.png
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database -q /usr/share/applications 2>/dev/null || true
    fi
fi

if [ "$1" = "purge" ]; then
    rm -rf /opt/zerousb
fi

exit 0
EOF
chmod 755 "${BUILD_ROOT}/DEBIAN/postrm"

# 10. Fix file permissions inside package
chmod 755 "${BUILD_ROOT}/opt/zerousb/run-gui.sh"
chmod 755 "${BUILD_ROOT}/opt/zerousb/scripts/"*.sh 2>/dev/null || true

# 11. Build the Debian package
echo "[+] Building deb archive with dpkg-deb..."
dpkg-deb --build --root-owner-group "${BUILD_ROOT}" "${DIST_DIR}/${DEB_NAME}"

# Clean build root
rm -rf "${BUILD_ROOT}"

echo ""
echo "================================================================="
echo "[✓] Debian package created successfully!"
echo "    File:     ${DIST_DIR}/${DEB_NAME}"
echo "    Size:     $(du -h "${DIST_DIR}/${DEB_NAME}" | awk '{print $1}')"
echo "    Install:  sudo dpkg -i ${DIST_DIR}/${DEB_NAME}"
echo "              sudo apt-get install -f"
echo "================================================================="
