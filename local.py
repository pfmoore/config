import os
import sys
import stat
import codecs
import shutil
from subprocess import check_call, call
from os.path import join

class EncodedText:
    bomtypes = ['UTF8', 'UTF16_BE', 'UTF16_LE', 'UTF32_BE', 'UTF32_LE']

    def __init__(self, bytestr):
        for bomtype in self.bomtypes:
            enc = 'utf-' + bomtype.lower().replace('_', '-')[3:]
            bom = getattr(codecs, 'BOM_' + bomtype)
            if bytestr.startswith(bom):
                self.encoding = enc
                self.bom = bom
                self.text = bytestr[len(bom):].decode(enc)
                return

        self.encoding = 'ascii'
        self.bom = None
        self.text = bytestr.decode('ascii', errors='surrogateescape')

    def to_bytes(self):
        if self.bom:
            return self.bom + self.text.encode(self.encoding)
        else:
            return self.text.encode(self.encoding, errors='surrogateescape')

def robocopy(src, dst):
    call(['robocopy', '/MIR', '/NFL', '/NDL', '/NJH', '/NJS', src, dst])

def make_path(spec):
    if isinstance(spec, tuple):
        newspec = []
        for elem in spec:
            if elem.startswith('$'):
                elem = os.environ[elem[1:]]
            newspec.append(elem)
        return join(*newspec)
    if spec.startswith('$'):
        spec = os.environ[spec[1:]]
    return spec

def copy(src, dst, filename=None):
    src = make_path(src)
    dst = make_path(dst)
    if filename:
        shutil.copyfile(join(src, filename), join(dst, filename))
    else:
        robocopy(src, dst)

def replace_env(filename, *varnames, expand=False):
    with open(filename, 'rb') as f:
        content = EncodedText(f.read())
    txt = content.text
    for varname in varnames:
        value = os.environ[varname]
        if expand:
            txt = txt.replace('%' + varname + '%', value)
        else:
            txt = txt.replace(value, '%' + varname + '%')
    content.text = txt
    with open(filename, 'wb') as f:
        f.write(content.to_bytes())

def cmd_apply():
    replace_env('TCC\\TCMD.INI', 'LOCALAPPDATA')

def cmd_remove():
    replace_env('TCC\\TCMD.INI', 'LOCALAPPDATA', expand=True)

def cmd_deploy():
    copy('Mercurial', '$USERPROFILE', 'Mercurial.ini')
    copy('Git', '$USERPROFILE', '.gitconfig')
    copy('Py', '$LOCALAPPDATA', 'py.ini')
    copy('TCC', ('$LOCALAPPDATA', 'JPSoft'))
    copy('Vim', ('$USERPROFILE', 'vimfiles'))
    check_call(['reg', 'import', 'ConEmu\\ConEmu.reg'])

def cmd_import():
    copy('$USERPROFILE', 'Mercurial', 'Mercurial.ini')
    copy('$USERPROFILE', 'Git', '.gitconfig')
    copy('$LOCALAPPDATA', 'Py', 'py.ini')
    copy(('$LOCALAPPDATA', 'JPSoft'), 'TCC')
    copy(('$USERPROFILE', 'vimfiles'), 'Vim')
    check_call(['reg', 'export', 'HKCU\\Software\\ConEmu\\.Vanilla', 'ConEmu\\ConEmu.reg', '/y'])

def cmd_clean():
    paths = ['Mercurial', 'Git', 'ConEmu', 'Vim', 'TCC', 'Py']
    for path in paths:
        if os.path.exists(path):
            def make_rw_del(action, name, exc):
                os.chmod(name, stat.S_IWRITE)
                os.remove(name)
            shutil.rmtree(path, onerror=make_rw_del)
        os.mkdir(path)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: {} [apply|remove|deploy|import]".format(os.path.basename(__file__)))
        sys.exit(1)
    cmds = {
        'apply': cmd_apply,
        'remove': cmd_remove,
        'deploy': cmd_deploy,
        'import': cmd_import,
        'clean': cmd_clean,
    }
    cmds[sys.argv[1]]()
