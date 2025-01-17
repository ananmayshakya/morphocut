"""Test morphocut.parallel."""


import os
import signal

import pytest
from timer_cm import Timer

from morphocut import Call, Node, Pipeline
from morphocut.parallel import ParallelPipeline
from morphocut.stream import Unpack
from tests.helpers import Sleep

import sys

if not sys.platform.startswith("linux"):
    pytest.skip(
        "skipping parallel tests on non-linux platforms", allow_module_level=True
    )

N_STEPS = 31


@pytest.mark.slow
@pytest.mark.xfail(reason="This test is nondeterministic.")
def test_speed():

    with Pipeline() as pipeline:
        level1 = Unpack(range(N_STEPS))
        level2 = Unpack(range(N_STEPS))
        Sleep()

    with Timer("sequential") as t:
        expected_result = [
            (obj[level1], obj[level2]) for obj in pipeline.transform_stream()
        ]

    elapsed_sequential = t.elapsed

    with Pipeline() as pipeline:
        level1 = Unpack(range(N_STEPS))
        with ParallelPipeline(4) as pp:
            level2 = Unpack(range(N_STEPS))
            Sleep()

    with Timer("parallel") as t:
        result = [(obj[level1], obj[level2]) for obj in pipeline.transform_stream()]

    elapsed_parallel = t.elapsed

    assert result == expected_result

    assert elapsed_parallel < elapsed_sequential


class SomeException(Exception):
    pass


@pytest.mark.slow
def test_exception_main_thread():

    with Pipeline() as pipeline:
        level1 = Unpack(range(N_STEPS))
        with ParallelPipeline(4) as pp:
            level2 = Unpack(range(N_STEPS))
            Sleep()

    stream = pipeline.transform_stream()

    try:
        with pytest.raises(SomeException):
            for i, obj in enumerate(stream):
                if i == 10:
                    raise SomeException()
    finally:
        stream.close()


class Raiser(Node):
    def transform(self):
        raise SomeException("foo")


@pytest.mark.slow
def test_exception_worker():

    with Pipeline() as pipeline:
        level1 = Unpack(range(N_STEPS))
        with ParallelPipeline(4) as pp:
            Sleep()
            Raiser()

    with pytest.raises(SomeException, match="foo"):
        pipeline.run()

    # TODO: Make sure that all processes are stopped


class KeyErrorRaiser(Node):
    def transform(self):
        raise KeyError("foo")


def test_KeyError():
    with Pipeline() as pipeline:
        with ParallelPipeline(4) as pp:
            KeyErrorRaiser()

    with pytest.raises(KeyError, match="foo"):
        pipeline.run()


def test_exception_upstream():

    with Pipeline() as pipeline:
        level1 = Unpack(range(N_STEPS))
        Raiser()
        with ParallelPipeline(4) as pp:
            level2 = Unpack(range(N_STEPS))

    with pytest.raises(SomeException, match="foo"):
        pipeline.run()


@pytest.mark.parametrize("num_workers", [1, 2, 3, 4])
def test_num_workers(num_workers):
    with Pipeline() as pipeline:
        level1 = Unpack(range(N_STEPS))
        with ParallelPipeline(num_workers) as pp:
            level2 = Unpack(range(N_STEPS))

    pipeline.run()


def test_worker_die():

    with Pipeline() as pipeline:
        level1 = Unpack(range(N_STEPS))
        with ParallelPipeline(4):
            Call(lambda: os.kill(os.getpid(), signal.SIGKILL))

    with pytest.raises(
        RuntimeError, match=r"Worker \d+ died unexpectedly. Exit code: -SIGKILL"
    ):
        pipeline.run()
