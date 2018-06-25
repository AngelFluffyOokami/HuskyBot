from aiohttp import web

from discord.ext import commands

import logging


LOG = logging.getLogger("DakotaBot.HTTPServer")


class WolfRouter:
    """
    A simple dynamic router that allows methods to be added/removed freely.
    """
    def __init__(self):
        self.routes = {}

    def add_route(self, method: str, path: str, plugin: str, handler):
        """
        Add a new route to the internal routing table.

        :param method: The method that this route should target.
        :param path: The path that this route should handle.
        :param plugin: The plugin name this works on
        :param handler: The function/def that will handle this route.
        """
        path_route = self.routes.setdefault(path, {})
        path_route[method.upper()] = {}

        path_route[method.upper()]['cog'] = plugin
        path_route[method.upper()]['func'] = handler

    def remove_method(self, path: str, method: str):
        """
        Remove a single routed method from the routing table.

        :param path: The path to target for removal.
        :param method: The method inside the path to delete.
        """
        path_route = self.routes.get(path, None)

        if path_route is None:
            raise ValueError("The specified path {} does not exist".format(path))

        del path_route[method.upper()]

    def remove_path(self, path: str):
        """
        Remove a specific path from our routing table.

        :param path: The path (and methods) to remove.
        """
        del self.routes[path]

    def remove_paths(self, path: str):
        """
        Remove all paths that start with the specified path string.

        :param path: The starting string to find and delete.
        """
        for p in self.routes:
            if p.startswith(path):
                del self.routes[p]

    def handle(self, bot: commands.Bot):
        async def wrapped(request: web.BaseRequest):
            if request.path not in self.routes:
                raise web.HTTPNotFound()

            path_routes = self.routes[request.path]

            if request.method not in path_routes:
                raise web.HTTPMethodNotAllowed(method=request.method, allowed_methods=path_routes.keys())

            method = path_routes[request.method]
            result = await method['func'](bot.get_cog(name=method['cog']), request=request)
            return result
        return wrapped


router = WolfRouter()


def get_router():
    return router


def register(path: str, methods: list):
    def decorator(f):
        """
        This is a ***dangerously ugly*** way of registering things with an otherwise pretty HTTP router.

        We need to be able to access plugin instance selfs, and decorators can't get those. Boo.
        """
        for method in methods:
            plugin = f.__qualname__.split('.')[-2]
            router.add_route(method, path, plugin, f)
            LOG.info("Registered HTTP endpoint \"{} {}\" for plugin {}".format(method, path, plugin))

    return decorator
