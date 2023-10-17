import mimetypes
import os
import sys
from collections.abc import Iterable

from .alias import StartResponse, WSGIEnvironment, WSGIApplication

__all__ = ['Main']


def static_url(path: str | None, default: str):
    if path is None:
        return default

    else:
        assert isinstance(path, str), \
            'URL for static files must be of string type'

        assert path.startswith('/'), \
            "URL for static files must begin with a slash: '%s'" % path

        assert path.endswith('/'), \
            "URL for static files must end with a slash: '%s'" % path

        return path


def directory_path(module_path: str, dirname: str | None, default: str):
    if dirname is None:
        dirname = default

    return os.path.abspath(os.path.join(module_path, dirname))


class Static:
    __slots__ = ('isdir', 'path', 'directory', 'encoding')

    isdir: bool
    path: str
    directory: str
    encoding: str

    def __init__(self, path: str, directory: str, encoding: str):
        self.isdir = os.path.isdir(directory)

        if self.isdir:
            for attr, value in (('path', path), ('directory', directory), ('encoding', encoding)):
                setattr(self, attr, value)

    def file(self, path_info: str):
        if self.isdir and path_info.startswith(self.path):
            if os.path.isfile(file := os.path.join(self.directory, path_info[len(self.path):])):
                return file


class Main(Static):
    def __init__(
            self: WSGIApplication,
            module_name: str,
            static_path: str = None,
            static_directory: str | os.PathLike = None,
            static_encoding: str = None,
    ):
        module_path = os.path.dirname(sys.modules[module_name].__file__)

        if static_encoding is None:
            static_encoding = 'utf-8'

        super().__init__(
            static_url(static_path, '/static/'),
            directory_path(module_path, static_directory, 'static'),
            static_encoding,
        )

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> Iterable[bytes]:
        if file := self.file(environ['PATH_INFO']):
            media_type, encoding = mimetypes.guess_type(file, strict=True)

            if media_type is None:
                media_type = 'text/plain'

            if media_type.startswith('text'):
                if os.path.getsize(file):
                    if encoding is None:
                        encoding = self.encoding

                    media_type = f"{media_type}{';'} charset={encoding}"

            start_response('200 OK', [('content-type', media_type)])

            return environ['wsgi.file_wrapper'](open(file, 'rb'))

        else:
            if '/' == environ['PATH_INFO']:
                body, status = b'Home page', '200 OK'

            else:
                body, status = b'Not Found', '404 Not Found'

            size, media_type = len(body), 'text/plain; charset=utf-8'

            start_response(status, [('content-length', str(size)), ('content-type', media_type)])

            return [body]
