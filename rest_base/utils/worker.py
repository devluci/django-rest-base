import inspect
import multiprocessing
import os
import random
import traceback
from typing import Callable, Union, Iterable, List, Tuple, Set, Optional

from django import db
from django.db.models import QuerySet

__all__ = ['WorkerPool']

WorkerTask = Set[list]
Task = Tuple[Callable, Optional[List[WorkerTask]], Optional[int], tuple, dict, str]


class WorkerPool:
    def __init__(
            self, worker_cnt: int, blocking: bool = True, log: Callable = None,
            verbose: bool = False, throw: bool = True
    ):
        self._pid = None
        self._log = log or print
        self._verbose = verbose
        self._throw = throw
        self.log(f'WorkerPool (size: {worker_cnt}) generated', debug=True)

        self._tasks: List[Task] = list()
        self._worker_cnt = worker_cnt
        self._blocking = blocking

    def __len__(self):
        return len(self._tasks)

    def __bool__(self):
        return bool(self._tasks)

    def _set_pid(self, pid: int):
        self._pid = pid

    def log(self, *args, debug: bool = False):
        if debug and not self._verbose:
            return
        if self._pid is None:
            self._log('[parent]', *args)
        else:
            self._log(f'[{self._pid}]', *args)

    def push(
            self, queryset_or_objects: Union[QuerySet, Iterable], func: Callable,
            *args, plural_name: str = None, **kwargs
    ):
        if type(queryset_or_objects) is QuerySet:
            objects = list(queryset_or_objects.order_by('?'))
            plural_name = plural_name or queryset_or_objects.model._meta.verbose_name_plural
        else:
            objects = random.sample(queryset_or_objects, k=len(queryset_or_objects))
            plural_name = plural_name or f'{func.__name__}s'

        if not objects:
            return

        task_size = (len(objects) + self._worker_cnt - 1) // self._worker_cnt
        worker_tasks: List[WorkerTask] = list()

        for w in range(self._worker_cnt):
            worker_tasks.append(set(objects[w * task_size:(w + 1) * task_size]))

        self._tasks.append((func, worker_tasks, task_size, args, kwargs, plural_name))
        self.log(f'distribute {task_size} / {len(objects)} {plural_name} (func: {func.__name__})', debug=True)

    def register(self, func: Callable, *args, func_name: str = None, **kwargs):
        func_name = func_name or func.__name__
        self._tasks.append((func, None, None, args, kwargs, func_name))
        self.log(f'register {func_name}', debug=True)

    def run(self, set_pid: Callable = None):
        if not self._tasks:
            self.log('no tasks to process', debug=True)
            return

        if set_pid is None:
            set_pid = self._set_pid

        self.log('spawning workers', debug=True)

        workers_pid = list()
        worker_task = [multiprocessing.JoinableQueue() for _ in range(self._worker_cnt)]
        db.connections.close_all()
        for w in range(self._worker_cnt):
            pid = os.fork()
            if pid:
                workers_pid.append(pid)
                continue
            try:
                set_pid(os.getpid())
                db.connection.connect()
                self.log('worker spawned', debug=True)

                for func, worker_tasks, task_size, args, kwargs, name in self._tasks:
                    if self._blocking:
                        worker_task[w].get()
                    try:
                        try:
                            if 'log' in inspect.signature(func).parameters.keys():
                                def func_log(*_args, **_kwargs):
                                    func(*_args, **_kwargs, log=self.log)
                            else:
                                func_log = func
                        except ValueError:
                            func_log = func

                        if worker_tasks is None:
                            self.log(f'process {name}')
                            func_log(*args, **kwargs)
                        else:
                            if worker_tasks[w]:
                                self.log(
                                    f'process {name}: {w * task_size} {w * task_size + len(worker_tasks[w])}',
                                    debug=True,
                                )
                                func_log(worker_tasks[w], *args, **kwargs)
                            else:
                                self.log(f'process {name}: none', debug=True)
                    except:
                        if self._throw:
                            raise
                        self.log('task failed')
                        self.log(traceback.format_exc())
                    finally:
                        if self._blocking:
                            worker_task[w].task_done()

                db.connections.close_all()
            except:
                self.log('worker failed')
                self.log(traceback.format_exc())
            finally:
                os._exit(0)

        if self._blocking:
            for _ in range(len(self._tasks)):
                for w in range(self._worker_cnt):
                    worker_task[w].put(None)
                for w in range(self._worker_cnt):
                    worker_task[w].join()
                self.log('task_done -> next_task', debug=True)

        for pid in workers_pid:
            os.waitpid(pid, 0)

        db.connection.connect()

        self._tasks.clear()
        self.log('all workers done', debug=True)
