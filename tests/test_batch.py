from typing import Sequence
from morphocut.batch import BatchPipeline
from morphocut.core import Call, Pipeline
from morphocut.stream import Unpack
import pytest
import itertools
from morphocut.stream import RemainingHint


def chunks(it, size):
    it = iter(it)
    while True:
        chunk = tuple(itertools.islice(it, size))
        if not chunk:
            break

        yield chunk


@pytest.mark.parametrize(
    "seq_len",
    [5, 10, 100, 111],
)
def test_BatchPipeline(seq_len):
    batch_size = 10
    values = list(range(seq_len))
    with Pipeline() as pipeline:
        a = Unpack(values)
        remaining0 = RemainingHint()
        with BatchPipeline(batch_size):
            # Inside BatchPipeline, a is a Sequence
            b = Call(sum, a)
            # remaining1 = RemainingHint()
        remaining2 = RemainingHint()

    result = list(pipeline.transform_stream())

    assert [r[a] for r in result] == values

    # Calculate expected values for b
    b_expected = [sum(chunk) for chunk in chunks(values, batch_size)]

    assert [r[b] for r in result[::batch_size]] == b_expected

    # print("remaining0", [r[remaining0] for r in result])
    # print("remaining1", [r[remaining1] for r in result])
    # print("remaining2", [r[remaining2] for r in result])

    assert [r[remaining0] for r in result] == [r[remaining2] for r in result]

def assert_(cond):
    assert cond

@pytest.mark.parametrize(
    "seq_len",
    [5, 10, 100, 111],
)
def test_BatchPipeline_groupby(seq_len):
    batch_size = 10
    values = list(range(seq_len))
    with Pipeline() as pipeline:
        a = Unpack(values)
        b = Unpack(values)
        with BatchPipeline(batch_size, groupby=a):
            # a is scalar, b is a sequence
            Call(lambda a: assert_(isinstance(a, int)), a)
            Call(lambda b: assert_(isinstance(b, Sequence)), b)

    result = list(pipeline.transform_stream())
