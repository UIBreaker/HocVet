"""Kiểm thử và đóng gói bản Windows; không đưa dữ liệu cá nhân vào gói."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import types

from app_info import APP_VERSION


def verify_bundled_sources(root):
    from PyInstaller.archive.readers import CArchiveReader
    root=Path(root)
    archive=CArchiveReader(str(root/'dist'/'Học Vẹt.exe')).open_embedded_archive('PYZ.pyz')
    def same(left,right):
        if isinstance(left,types.CodeType):
            return isinstance(right,types.CodeType) and left.co_code==right.co_code and left.co_names==right.co_names and len(left.co_consts)==len(right.co_consts) and all(same(a,b) for a,b in zip(left.co_consts,right.co_consts))
        return left==right
    for name in ('ui','core','app_info','ui_theme','retro_controls','record_notice','overlay_input',
                 'workspace','workspace_ui','his_environment','extensions_ui','sheet_grid','clipboard_text','date_paste','focused_input','single_instance'):
        bundled=archive.extract(name)
        source=compile((root/(name+'.py')).read_bytes(),bundled.co_filename,'exec')
        if not same(bundled,source):raise ValueError(f'File đóng gói còn mã cũ: {name}. Hãy tạo lại thư mục build của phiên bản này.')


def package_release(root):
    root = Path(root)
    dist = root / 'dist'
    exe = dist / 'HocVet.exe'
    shutil.copy2(dist / 'Học Vẹt.exe', exe)
    archive = dist / f'HocVet-v{APP_VERSION}-Windows.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
        package.write(exe, 'Học Vẹt.exe')
        for name in ('README.md', 'RELEASE_NOTES.md', 'LICENSE'):
            package.write(root / name, name)
        for image in sorted((root / 'docs' / 'images').glob('*.png')):
            package.write(image, f'docs/images/{image.name}')
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise ValueError('Gói ZIP không toàn vẹn.')
    checksums = []
    for path in (exe, archive):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        checksums.append(f'{digest.hexdigest()}  {path.name}')
    checksum_file = dist / 'SHA256SUMS.txt'
    checksum_file.write_text('\n'.join(checksums) + '\n', encoding='utf-8')
    return exe, archive, checksum_file


if __name__ == '__main__':
    project = Path(__file__).resolve().parent
    for command in (
            [sys.executable, '-X', 'utf8', 'test_core.py'],
            [sys.executable, '-X', 'utf8', '-m', 'unittest', '-v', 'test_features', 'test_theme', 'test_workspace', 'test_overlay_input', 'test_his', 'test_date_paste', 'test_single_instance'],
            [sys.executable, '-m', 'PyInstaller', '--noconfirm','--workpath',str(project/'build'/f'release-{APP_VERSION}'),'HocVet.spec']):
        subprocess.run(command, cwd=project, check=True)
    verify_bundled_sources(project)
    for artifact in package_release(project):
        print(artifact)
