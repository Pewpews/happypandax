from contextlib import contextmanager
from abc import ABCMeta, abstractmethod
from inspect import isclass

from happypanda.common import utils, hlogger, exceptions
from happypanda.core import plugins

log = hlogger.Logger(__name__)


def get_available_commands():
    subs = utils.all_subclasses(Command)
    commands = set()
    for c in subs:
        c._get_commands()
        for a in c._entries:
            commands.add(c.__name__ + '.' + c._entries[a].name)
    return commands


class Command:
    "Base command"
    __metaclass__ = ABCMeta

    _events = {}
    _entries = {}

    def __init__(self, **kwargs):
        self._get_commands()

    @classmethod
    def _get_commands(cls):
        ""
        for a in cls.__dict__.values():
            if isinstance(a, CommandEvent):
                a.command_cls = cls
                cls._events[a.name] = a

            if isinstance(a, CommandEntry):
                a.command_cls = cls
                cls._entries[a.name] = a

    @abstractmethod
    def main(self, *args, **kwargs):
        pass

    def run(self, *args, **kwargs):
        """
        Run the command with *args and **kwargs.
        """
        log.d("Running command:", self.__class__.__name__)
        return self.main(*args, **kwargs)


class UndoCommand(Command):
    "Command capable of undoing itself"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abstractmethod
    def undo(self):
        pass


class _CommandPlugin:
    ""

    command_cls = None

    def __init__(self, name, *args, description='', **kwargs):
        self.name = name
        self._args_types = args
        self._kwargs_types = kwargs
        self._description = description

    def qualifiedname(self):
        "Returns Class.command name"
        return self.command_cls.__name__ + '.' + self.name

    def invoke_on_plugins(self, *args, **kwargs):
        "Invoke all plugins"
        self._check_types(*args, **kwargs)
        return plugins.registered.call_command(
            self.qualifiedname(), *args, **kwargs)

    def _ensure_class(self, type1, type2):
        if isclass(type1):
            return issubclass(type1, type2)
        return False

    def _check_types(self, *args, **kwargs):
        tr = []
        tr.append(len(args) == len(self._args_types))
        tr.append(all(isinstance(y, x) or self._ensure_class(y, x)
                      for x, y in zip(self._args_types, args)))

        tr.append(all(x in self._kwargs_types for x in kwargs))
        tr.append(all(isinstance(kwargs[x], self._kwargs_types[x]) or self._ensure_class(kwargs[x], self._kwargs_types[x])
                      for x in kwargs if x in self._kwargs_types))
        if not all(tr):
            raise exceptions.CoreError(
                utils.this_function(),
                "Wrong types were used for command '{}'. Types used {}, types expected {}".format(
                    self.qualifiedname(),
                    self._stringify_args(args, kwargs),
                    self._stringify_args(self._args_types, self._kwargs_types, True)))

    def _stringify_args(self, args, kwargs, is_type=False):
        ""
        s = '('
        if is_type:
            s += ", ".join(str(x) for x in args)
            s += ", ".join(x + '=' + str(y) for x, y in kwargs.items())
        else:
            s += ", ".join(str(type(x)) for x in args)
            s += ", ".join(x + '=' + str(type(y)) for x, y in kwargs.items())

        s += ')'

        return s


class CommandEvent(_CommandPlugin):
    "Base command event"

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)

    def emit(self, *args, **kwargs):
        "emit this event with *args and **kwargs"
        self.invoke_on_plugins(*args, **kwargs)


class CommandEntry(_CommandPlugin):
    "Base command entry"

    def __init__(self, name, return_type, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.return_type = return_type
        self.default_handler = None
        self.default_capture_handlers = []

    def default(self, capture=False):
        "Set a default handler. Only one default handler is allowed"

        def wrapper(func):
            if capture:
                self.default_capture_handlers.append(func)
                return func

            if self.default_handler:
                raise exceptions.CoreError(
                    utils.this_function(),
                    "Command '{}' has already been assigned a default handler".format(
                        self.name))
            self.default_handler = func
            return func
        return wrapper

    @contextmanager
    def call_capture(self, token, *args, **kwargs):
        "Calls associated handlers with a capture token"
        handler = self.invoke_on_plugins(*args, **kwargs)
        handler.default_handler = self.default_handler
        handler.expected_type = self.return_type
        handler.capture = True
        handler.capture_token = token
        for h in self.default_capture_handlers:
            handler._add_capture_handler(h)
        yield handler

    @contextmanager
    def call(self, *args, **kwargs):
        "Calls associated handlers"
        handler = self.invoke_on_plugins(*args, **kwargs)
        handler.default_handler = self.default_handler
        handler.expected_type = self.return_type
        yield handler