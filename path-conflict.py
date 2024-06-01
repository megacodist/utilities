#
# 
#
"""This program looks for duplicate external commands in the Terminal.
"""

import logging
from queue import Queue, Empty
from pathlib import Path
import sys
from threading import Thread


_EXES = ['.exe', '.com', '.bat', '.cmd',]
"""A list of all file extensions of interest."""

_CASE_SEN = Path('A') == Path('a')
"""Specifies whether the underlying filesystem is case sensitive or not."""


class Error:
    message: str
    canContinue: bool = True

    def __init__(
            self,
            message: str,
            can_continue: bool = True,
            ) -> None:
        self.message = message
        self.canContinue = can_continue


class PathCheckerThrd(Thread):
    def __init__(self, q: Queue[str | Error | dict[str, list[str]]]) -> None:
        super().__init__(
            None,
            None,
            'Path environment variable conflict checkers',
            tuple(),
            None,
            daemon=None)
        self._q = q
        """The messaging queue."""
    
    def run(self) -> None:
        # Declaring variables -----------------------------
        from collections import defaultdict
        import os
        from pathlib import Path
        global _EXES
        global _CASE_SEN
        # Searching for conflicts -------------------------
        pathEnviron = os.environ.get('path')
        if pathEnviron is None:
            self._q.put(Error('no `path` environment variable.', False))
            return
        allCmdFiles: dict[Path, list[Path]] = defaultdict(list)
        pathDirs = pathEnviron.split(';')
        for dir_ in pathDirs:
            dir_ = os.path.expandvars(dir_)
            pthDir = Path(dir_)
            self._q.put(f'Investigating {str(pthDir)}')
            cmdFiles = list[Path]()
            for ext in _EXES:
                cmdFiles.extend(pthDir.glob(f'*{ext}'))
            cmdFiles = [file.relative_to(pthDir) for file in cmdFiles]
            for cmdFile in cmdFiles:
                allCmdFiles[cmdFile].append(pthDir)
        self._q.put('Analyzing')
        allCmdFiles = {
            key:value
            for key, value in allCmdFiles.items()
            if len(value) > 1}
        dupCmdFiles: dict[str, list[str]] = {}
        for key, dirs in allCmdFiles.items():
            stDirs = set(dirs)
            if len(stDirs) == 1:
                continue
            newDirs: list[str] = []
            for dir_ in dirs:
                if dir_ in stDirs:
                    stDirs.remove(dir_)
                    newDirs.append(str(dir_))
            key = key.stem if _CASE_SEN else key.stem.lower()
            dupCmdFiles[key] = newDirs
        self._q.put(dupCmdFiles)


def main() -> None:
    from time import monotonic, sleep
    print('=' * 40)
    print(__doc__)
    print('=' * 40)
    spinners = r'▖▘▝▗'
    q = Queue[str | Error | dict[str, list[str]]]()
    pathCheckerThrd = PathCheckerThrd(q)
    pathCheckerThrd.start()
    lenSpinner = len(spinners)
    stTime = monotonic()
    while True:
        try:
            product = q.get_nowait()
            if isinstance(product, str):
                print(' ', end='\r', flush=True)
                print(product)
            elif isinstance(product, Error):
                print(' ', end='\r', flush=True)
                print(product.message)
                if not product.canContinue:
                    sys.exit(1)
            elif isinstance(product, dict):
                break
            else:
                logging.error(f'An unknown result: {repr(product)}')
        except Empty:
            cuTime = monotonic()
            idxSpinner = int((cuTime - stTime) * 2) % lenSpinner
            print(spinners[idxSpinner], end='\r', flush=True)
            sleep(0.25)
    if product:
        print('Duplicate commands in CMD:')
        for idx, cmd in enumerate(product, 1):
            print(f'\t{idx}: {cmd}')
            for dir_ in product[cmd]:
                print(f'\t\t{dir_}')
    else:
        print('No duplicate CMD command was found.')


if __name__ == '__main__':
    main()
