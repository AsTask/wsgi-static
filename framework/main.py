import mimetypes
import os
import sys
from collections.abc import Iterable

from .alias import StartResponse, WSGIEnvironment, WSGIApplication

__all__ = ['Main']


def static(url: str | None, default: str):
    if url is None:
        return default

    else:
        assert isinstance(url, str), \
            'URL for static files must be of string type'

        assert url.startswith('/'), \
            "URL for static files must begin with a slash: '%s'" % url

        assert url.endswith('/'), \
            "URL for static files must end with a slash: '%s'" % url

        return url


def directory_path(module_path: str, dirname: str | None, default: str):
    if dirname is None:
        dirname = default

    return os.path.abspath(os.path.join(module_path, dirname))


class Static:
    __slots__ = ('isdir', 'url', 'directory', 'encoding')

    isdir: bool
    url: str
    directory: str
    encoding: str

    def __init__(self, url: str, directory: str, encoding: str):
        self.isdir = os.path.isdir(directory)

        if self.isdir:
            for attr, value in (('url', url), ('directory', directory), ('encoding', encoding)):
                setattr(self, attr, value)

    def file(self, path_info: str):
        if self.isdir and path_info.startswith(self.url):
            if os.path.isfile(file := os.path.join(self.directory, path_info[len(self.url):])):
                return file


class Main(Static):
    def __init__(
            self: WSGIApplication,
            module_name: str,
            static_url: str = None,
            static_directory: str | os.PathLike = None,
            static_encoding: str = None,
    ):
        module_path = os.path.dirname(sys.modules[module_name].__file__)

        if static_encoding is None:
            static_encoding = 'utf-8'

        super().__init__(
            static(static_url, '/static/'),
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
