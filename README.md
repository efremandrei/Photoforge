# PhotoForge3D

PhotoForge3D reconstructs a real 3D surface from overlapping photographs and prepares an STL for a slicer. Android captures/imports photos; a Windows PC runs COLMAP 4.2.1 and OpenMVS 2.4.0 on the CPU. The PC app also works independently with photos from any camera. No paid reconstruction API or cloud account is required.

Source repository: [efremandrei/Photoforge](https://github.com/efremandrei/Photoforge). The initial version 1.0.0 downloads are hosted at the release link below.

## Start

1. Download the Windows package from [Releases](https://github.com/efremandrei/PhotoForge3D/releases), extract the entire ZIP into a writable folder, and open `PhotoForge3D-PC.exe`. Keep the included `_internal` and `tools` folders beside it.
2. Install `PhotoForge3D-v1.0.0-build-1.apk` on an Android 10+ phone. It contains no native ABI libraries and supports Samsung arm64 devices.
3. On the PC, click **Connect Android phone**. On the phone, enter the displayed PC address and pairing code, then click **Connect**. Use the same trusted home Wi-Fi and allow the PC app on **private networks** if Windows asks. HTTP on the local network is unencrypted. Photos are sent only to the address you enter; they are stored on the PC in its `jobs` folder.
4. Take or import photos and tap **Reconstruct on PC**. Keep the PC app open; reconstruction continues if you leave the phone app. Reopen it to restore the selected scan and its progress. CPU processing can take minutes to hours, depending on the photo set.
5. Rotate the preview, crop background using X/Y/Z percentage ranges, enter the desired **longest dimension in millimetres**, and choose **Prepare & save STL**. Android asks where to save the file. The PC can import photos and save an STL without a phone.

## Capture for usable geometry

Keep the object stationary and move the camera around it. Aim for 30–80 sharp photographs, with 70–80% overlap, in rings at several heights. Include the top, low angles, and every surface you need. Avoid switching lenses or using zoom. Use diffuse light and a matte, textured object. Transparent, reflective, plain and moving objects are difficult. A turntable with a stationary unmasked background can confuse camera alignment.

The app accepts 8–240 distinct photos (20 MB per photo, 500 MB per upload, at least 320 pixels on the shorter side). It corrects EXIF rotation and works at up to 1600 pixels for a manageable first version. A large, thin or intricate object may need a higher-resolution reconstruction workflow.

Photos alone do not establish an absolute scale. Entering a size scales the reconstructed model; it does not calibrate or certify its physical dimensions. The longest dimension applies **after cropping and removing disconnected fragments**, which keeps the largest connected surface. Inspect the preview to make sure the intended object, rather than its background, is selected.

## Surface repair and printing

The original `surface.ply` is retained. Small holes may be filled during preparation. Larger open surfaces block STL export until you retake missing angles or explicitly enable **Seal gaps**. Gap sealing uses voxel closure and can thicken surfaces, remove fine detail, merge features, and infer unseen geometry. It is not a recovery of the true hidden surface. Always compare the result with the object.

The saved STL is reopened and checked for a watertight, consistently oriented positive-volume solid. This does not guarantee absence of every self-intersection, adequate wall thickness, dimensional accuracy, or suitability for a particular printer. Open it in your slicer, inspect it, set orientation, supports and printer settings. STL coordinates are exported in millimetres; STL itself has no unit metadata.

## Build from source

Windows x64 and Python 3.10 are tested. Run `powershell -ExecutionPolicy Bypass -File setup.ps1`, then `Start-PC.cmd`. Run checks with `.venv\Scripts\python.exe -m pytest -q` after installing `pytest` and `httpx`.

Build Android with JDK 17+ and Android SDK 35: `android\gradlew.bat -p android :app:assembleDebug :app:lintDebug`. Set your SDK path in `android/local.properties`. The distribution APK is signed with the persistent local release key in `.signing`, which is intentionally excluded from Git. Preserve that key and application ID `com.efremandrei.photoforge3d` for future updates; increase both versionName and versionCode. Do not substitute a debug key for an update to the distributed APK.

## Verification

The real pipeline reconstructed all 11 views from the [official OpenMVG Sceaux Castle dataset](https://github.com/openMVG/ImageDataset_SceauxCastle). Its raw surface contained 146,332 triangles; explicit sealing produced a verified 149,584-triangle STL with longest dimension 100 mm. This exercises the engines and export path using an architectural scene. It does **not** validate object-scanning accuracy or physical printing. See `docs/VERIFICATION.md` for release checks and device limitations.

## License and author

AGPL-3.0-or-later. COLMAP is BSD licensed; OpenMVS is AGPL-3.0. See `THIRD_PARTY.md` and the included notices. Corresponding application source is available in this repository; engine source is linked with exact release versions.

Andrei Efremuahkin · andrei.efr@gmail.com · version 1.0.0, build 1.
