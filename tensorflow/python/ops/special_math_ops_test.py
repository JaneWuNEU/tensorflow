# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Tests for tensorflow.python.ops.special_math_ops."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import opt_einsum
import six

from tensorflow.python.client import session
from tensorflow.python.eager import context
from tensorflow.python.framework import constant_op
from tensorflow.python.framework import dtypes
from tensorflow.python.framework import errors
from tensorflow.python.framework import ops
from tensorflow.python.framework import tensor_shape
from tensorflow.python.framework import test_util
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import gradient_checker_v2
from tensorflow.python.ops import math_ops
from tensorflow.python.ops import special_math_ops
from tensorflow.python.ops import variables
from tensorflow.python.platform import benchmark
from tensorflow.python.platform import test
from tensorflow.python.platform import tf_logging

class LBetaTest(test.TestCase):

  @test_util.run_in_graph_and_eager_modes
  def test_one_dimensional_arg(self):
    # Should evaluate to 1 and 1/2.
    x_one = [1, 1.]
    x_one_half = [2, 1.]
    with self.session(use_gpu=True):
      self.assertAllClose(
          1, self.evaluate(math_ops.exp(special_math_ops.lbeta(x_one))))
      self.assertAllClose(
          0.5, self.evaluate(math_ops.exp(special_math_ops.lbeta(x_one_half))))
      self.assertEqual([], special_math_ops.lbeta(x_one).get_shape())

  @test_util.run_deprecated_v1
  def test_one_dimensional_arg_dynamic(self):
    # Should evaluate to 1 and 1/2.
    x_one = [1, 1.]
    x_one_half = [2, 1.]
    with self.session(use_gpu=True):
      ph = array_ops.placeholder(dtypes.float32)
      beta_ph = math_ops.exp(special_math_ops.lbeta(ph))
      self.assertAllClose(1, beta_ph.eval(feed_dict={ph: x_one}))
      self.assertAllClose(0.5,
                          beta_ph.eval(feed_dict={ph: x_one_half}))

  @test_util.run_deprecated_v1
  def test_four_dimensional_arg_with_partial_shape_dynamic(self):
    x_ = np.ones((3, 2, 3, 4))
    # Gamma(1) = 0! = 1
    # Gamma(1 + 1 + 1 + 1) = Gamma(4) = 3! = 6
    # ==> Beta([1, 1, 1, 1])
    #     = Gamma(1) * Gamma(1) * Gamma(1) * Gamma(1) / Gamma(1 + 1 + 1 + 1)
    #     = 1 / 6
    expected_beta_x = 1 / 6 * np.ones((3, 2, 3))
    with self.session(use_gpu=True):
      x_ph = array_ops.placeholder(dtypes.float32, [3, 2, 3, None])
      beta_ph = math_ops.exp(special_math_ops.lbeta(x_ph))
      self.assertAllClose(expected_beta_x,
                          beta_ph.eval(feed_dict={x_ph: x_}))

  @test_util.run_in_graph_and_eager_modes
  def test_two_dimensional_arg(self):
    # Should evaluate to 1/2.
    x_one_half = [[2, 1.], [2, 1.]]
    with self.session(use_gpu=True):
      self.assertAllClose(
          [0.5, 0.5],
          self.evaluate(math_ops.exp(special_math_ops.lbeta(x_one_half))))
      self.assertEqual((2,), special_math_ops.lbeta(x_one_half).get_shape())

  @test_util.run_deprecated_v1
  def test_two_dimensional_arg_dynamic(self):
    # Should evaluate to 1/2.
    x_one_half = [[2, 1.], [2, 1.]]
    with self.session(use_gpu=True):
      ph = array_ops.placeholder(dtypes.float32)
      beta_ph = math_ops.exp(special_math_ops.lbeta(ph))
      self.assertAllClose([0.5, 0.5],
                          beta_ph.eval(feed_dict={ph: x_one_half}))

  @test_util.run_in_graph_and_eager_modes
  def test_two_dimensional_proper_shape(self):
    # Should evaluate to 1/2.
    x_one_half = [[2, 1.], [2, 1.]]
    with self.session(use_gpu=True):
      self.assertAllClose(
          [0.5, 0.5],
          self.evaluate(math_ops.exp(special_math_ops.lbeta(x_one_half))))
      self.assertEqual(
          (2,),
          self.evaluate(array_ops.shape(special_math_ops.lbeta(x_one_half))))
      self.assertEqual(
          tensor_shape.TensorShape([2]),
          special_math_ops.lbeta(x_one_half).get_shape())

  @test_util.run_in_graph_and_eager_modes
  def test_complicated_shape(self):
    with self.session(use_gpu=True):
      x = ops.convert_to_tensor(np.random.rand(3, 2, 2))
      self.assertAllEqual(
          (3, 2), self.evaluate(array_ops.shape(special_math_ops.lbeta(x))))
      self.assertEqual(
          tensor_shape.TensorShape([3, 2]),
          special_math_ops.lbeta(x).get_shape())

  @test_util.run_in_graph_and_eager_modes
  def test_length_1_last_dimension_results_in_one(self):
    # If there is only one coefficient, the formula still works, and we get one
    # as the answer, always.
    x_a = [5.5]
    x_b = [0.1]
    with self.session(use_gpu=True):
      self.assertAllClose(
          1,
          self.evaluate(math_ops.exp(special_math_ops.lbeta(x_a))),
          rtol=3e-6)
      self.assertAllClose(
          1, self.evaluate(math_ops.exp(special_math_ops.lbeta(x_b))))
      self.assertEqual((), special_math_ops.lbeta(x_a).get_shape())

  @test_util.run_in_graph_and_eager_modes
  def test_empty_rank1_returns_negative_infinity(self):
    with self.session(use_gpu=True):
      x = constant_op.constant([], shape=[0])
      lbeta_x = special_math_ops.lbeta(x)
      expected_result = constant_op.constant(-np.inf, shape=())

      self.assertAllEqual(self.evaluate(expected_result),
                          self.evaluate(lbeta_x))
      self.assertEqual(expected_result.get_shape(), lbeta_x.get_shape())

  @test_util.run_in_graph_and_eager_modes
  def test_empty_rank2_with_zero_last_dim_returns_negative_infinity(self):
    with self.session(use_gpu=True):
      event_size = 0
      for batch_size in [0, 1, 2]:
        x = constant_op.constant([], shape=[batch_size, event_size])
        lbeta_x = special_math_ops.lbeta(x)
        expected_result = constant_op.constant(-np.inf, shape=[batch_size])

        self.assertAllEqual(self.evaluate(expected_result),
                            self.evaluate(lbeta_x))
        self.assertEqual(expected_result.get_shape(), lbeta_x.get_shape())

  @test_util.run_in_graph_and_eager_modes
  def test_empty_rank2_with_zero_batch_dim_returns_empty(self):
    with self.session(use_gpu=True):
      batch_size = 0
      for event_size in [0, 1, 2]:
        x = constant_op.constant([], shape=[batch_size, event_size])
        lbeta_x = special_math_ops.lbeta(x)

        expected_result = constant_op.constant([], shape=[batch_size])

        self.assertAllEqual(self.evaluate(expected_result),
                            self.evaluate(lbeta_x))
        self.assertEqual(expected_result.get_shape(), lbeta_x.get_shape())


class BesselTest(test.TestCase):

  @test_util.run_in_graph_and_eager_modes
  def test_bessel_i0(self):
    x_single = np.arange(-3, 3).reshape(1, 3, 2).astype(np.float32)
    x_double = np.arange(-3, 3).reshape(1, 3, 2).astype(np.float64)
    try:
      from scipy import special  # pylint: disable=g-import-not-at-top
      self.assertAllClose(special.i0(x_single),
                          self.evaluate(special_math_ops.bessel_i0(x_single)))
      self.assertAllClose(special.i0(x_double),
                          self.evaluate(special_math_ops.bessel_i0(x_double)))
    except ImportError as e:
      tf_logging.warn('Cannot test special functions: %s' % str(e))

  @test_util.run_in_graph_and_eager_modes
  def test_bessel_i1(self):
    x_single = np.arange(-3, 3).reshape(1, 3, 2).astype(np.float32)
    x_double = np.arange(-3, 3).reshape(1, 3, 2).astype(np.float64)
    try:
      from scipy import special  # pylint: disable=g-import-not-at-top
      self.assertAllClose(special.i1(x_single),
                          self.evaluate(special_math_ops.bessel_i1(x_single)))
      self.assertAllClose(special.i1(x_double),
                          self.evaluate(special_math_ops.bessel_i1(x_double)))
    except ImportError as e:
      tf_logging.warn('Cannot test special functions: %s' % str(e))


@test_util.run_all_in_graph_and_eager_modes
class EinsumTest(test.TestCase):

  def _check(self, s, *input_shapes, **kwargs):
    dtype = kwargs.pop('dtype', np.float32)
    r = np.random.RandomState(0)
    inputs = []
    for shape in input_shapes:
      arr = np.array(r.randn(*shape)).astype(dtype)
      if dtype == np.complex64 or dtype == np.complex128:
        arr += 1j * np.array(r.randn(*shape)).astype(dtype)
      inputs.append(arr)
    input_tensors = [constant_op.constant(x, shape=x.shape) for x in inputs]
    a = np.einsum(s, *inputs)
    b = self.evaluate(special_math_ops.einsum(s, *input_tensors))
    self.assertAllClose(a, b, atol=1e-4, rtol=1e-4)

  def test_invalid_keyword_arguments(self):
    r = np.random.RandomState(0)
    a = array_ops.placeholder_with_default(r.randn(2, 3), shape=(2, 3))
    b = array_ops.placeholder_with_default(r.randn(3, 4), shape=(3, 4))
    with self.assertRaises(TypeError):
      _ = special_math_ops.einsum(
          'ij,jk->ik', a, b, name='name', invalid1='value1', invalid2='value2')

  def test_unary(self):
    self._check('a', (3,))
    self._check('aa', (3, 3))
    self._check('ab->', (3, 3))
    self._check('ab->ab', (3, 3))
    self._check('abc->b', (3, 4, 5))
    self._check('abc->ca', (3, 4, 5))
    self._check('abc->cab', (3, 4, 5))

    # Empty cases.
    self._check('', ())
    self._check('->', ())

    # Repeated indices cases.
    self._check('aa->', (3, 3))
    self._check('aa->a', (3, 3))
    self._check('aaa->', (3, 3, 3))
    self._check('aaa->a', (3, 3, 3))
    self._check('aab->a', (3, 3, 4))
    self._check('aabcc->a', (3, 3, 5, 4, 4))
    self._check('aabcc->ac', (3, 3, 5, 4, 4))
    self._check('aabcd->ad', (3, 3, 5, 4, 4))

  def test_unary_ellipsis(self):
    self._check('...->', ())
    self._check('...ijk->...ki', (3, 4, 5))
    self._check('...ijk->...ki', (1, 3, 4, 5))
    self._check('...ijk->...ki', (2, 2, 3, 4, 5))
    self._check('...ij->...ji', (5, 2, 3))  # batch matrix transpose
    self._check('...ij->...', (5, 2, 3))  # batch sum

    self._check('...->...', ())
    self._check('->...', ())

    # Repeated indices.
    self._check('i...ii->...i', (3, 2, 3, 3))
    self._check('i...i->i...', (2, 2))
    self._check('i...i->', (2, 2))
    self._check('i...i->...', (2, 5, 1, 2))
    self._check('i...i->i...', (2, 1, 2))
    self._check('i...i->i...', (2, 3, 4, 5, 2))

  def test_binary_simple(self):
    # Binary cases in XLA mode must have either (a) each index appearing exactly
    # once in both the inputs (batch or contraction index), or (b) appearing
    # exactly once in an input and in the output (free index).
    self._check(',->', (), ())
    self._check('a,a->', (3,), (3,))
    self._check('a,a->a', (3,), (3,))
    self._check('ab,b->a', (3, 4), (4,))
    self._check('ab,ab->', (3, 4), (3, 4))
    self._check('ab,bc->ac', (3, 4), (4, 5))
    self._check('nij,jk->nik', (5, 2, 3), (3, 4))
    self._check('abc,bad->abcd', (1, 2, 3), (2, 1, 4))
    # Based on https://github.com/google/jax/issues/37#issuecomment-448572187
    self._check('sa,shb->shab', (2, 1), (2, 3, 4))
    # Infer the output subscripts.
    self._check('ab,b', (3, 4), (4,))
    self._check('cab,b', (1, 3, 4), (4,))

  def test_reduced_indices(self):
    self._check('ba,b->', (3, 2), (3,))
    self._check('ab,ab->', (3, 4), (3, 4))

  def test_repeated_indices(self):
    # Repeated indices.
    self._check('ijj,k->ik', (2, 3, 3), (4,))
    self._check('aba,a->b', (3, 4, 3), (3,))
    # From https://github.com/dask/dask/pull/3412#discussion_r182413444
    self._check('aab,bc->ac', (2, 2, 3), (3, 4))
    self._check('aab,bcc->ac', (2, 2, 3), (3, 4, 4))

  def test_binary_ellipsis(self):
    # Batch matmul with ellipsis but without broadcasting.
    self._check('...mk,...kn->...mn', (5, 1, 2, 3), (5, 1, 3, 4))
    # Empty batch dimensions.
    self._check('...mk,...kn->...mn', (2, 3), (3, 4))
    # Tensor contraction with transpose.
    self._check('...ija,aijb...->ba...ij', (1, 2, 2, 3, 1), (1, 2, 3, 4, 1, 2))
    # Output subscripts may omit ellipsis when batch shape is empty.
    self._check('...mk,...kn->mn', (2, 3), (3, 4))
    self._check('...mk,kn->mn', (2, 3), (3, 4))
    self._check('mk,...kn->mn', (2, 3), (3, 4))
    self._check('...,...->...', (2, 3), (2, 3))  # hadamard product
    self._check('...i,...j->...ij', (5, 2), (5, 3))  # outer product

  def test_broadcasting(self):
    # Batch matmul with broadcasting.
    self._check('...ij,...jk->...ik', (1, 2, 3), (3, 5))
    self._check('...ij,...jk->...ik', (2, 3), (1, 3, 5))
    self._check('...ij,...jk->...ik', (5, 2, 3), (3, 5))
    self._check('...ij,...jk->...ik', (2, 3), (5, 3, 5))
    self._check('...ij,...jk->...ik', (3, 1, 2, 3), (1, 1, 7, 3, 5))
    self._check('i...j,j...k->...ik', (2, 1, 3, 1, 3), (3, 1, 7, 5))

    # Broadcasting with repeated indices.
    self._check('ij,jk...k->i...', (3, 2), (2, 4, 1, 4))
    self._check('ij,jk...k->...i', (3, 2), (2, 4, 5, 4))
    self._check('ijj,jk...k->i...', (3, 2, 2), (2, 4, 1, 4))
    self._check('i...jj,jk...k->i...', (3, 3, 1, 2, 2), (2, 4, 1, 5, 4))
    # Following 2 from https://stackoverflow.com/a/19203475/1611416
    self._check('...abc,...abcd->...d', (1, 1, 2, 3, 4), (5, 2, 3, 4, 6))
    self._check('ab...,b->ab...', (2, 3, 1, 1, 5), (3,))

  def test_dtypes(self):
    dtypes = []
    if test.is_built_with_rocm():
      # This test triggers the BLAS op calls on the GPU
      # ROCm does not support BLAS operations for complex types
      dtypes = [np.float64, np.float32]
    else:
      dtypes = [np.float64, np.float32, np.complex64, np.complex128]
    for dtype in dtypes:
      self._check('ij,jk->ik', (2, 2), (2, 2), dtype=dtype)
      self._check('ji,jk->ik', (2, 2), (2, 2), dtype=dtype)
      self._check('ji,kj->ik', (2, 2), (2, 2), dtype=dtype)
      self._check('ij,jk->ki', (2, 2), (2, 2), dtype=dtype)
      self._check('ji,kj->ki', (2, 2), (2, 2), dtype=dtype)

  def test_multiple_inputs(self):
    self._check('ijk,ijl,ikl->i', (1, 2, 3), (1, 2, 4), (1, 3, 4))
    self._check('i,ijk,j->k', (1,), (1, 2, 4), (2,))
    self._check('ij,ij,jk,kl->il', (1, 2), (1, 2), (2, 3), (3, 4))
    # Tests from dask.
    self._check('a,b,c', (5,), (7,), (9,))
    self._check('ab,ab,c->c', (5, 6), (5, 6), (2,))

  @test_util.disable_xla('b/131919749')
  def test_placeholder(self):

    def check(equation, *input_and_placeholder_shapes):
      r = np.random.RandomState(0)
      inputs = []
      input_placeholders = []
      for actual_shape, placeholder_shape in input_and_placeholder_shapes:
        input_np = np.array(r.randn(*actual_shape))
        inputs.append(input_np)
        input_placeholders.append(
            array_ops.placeholder_with_default(input_np, placeholder_shape))

      a = np.einsum(equation, *inputs)
      b = self.evaluate(special_math_ops.einsum(equation, *input_placeholders))
      self.assertAllClose(a, b, atol=1e-4, rtol=1e-4)

    check('bijl,bjkm->bik', ((9, 2, 3, 5), (None, None, None, 5)),
          ((9, 3, 4, 7), (None, None, 4, None)))
    check('...ij,...->...i', ((4, 3, 1, 2), (None, 3, None, 2)),
          ((4, 3), (None, 3)))

    # Ellipsis with unknown rank.
    check('bijl,bjkm->bik', ((9, 2, 3, 5), None), ((9, 3, 4, 7), None))
    check('...ij,...jk->...ik', ((3, 1, 2, 3), None), ((1, 7, 3, 4), None))

  def test_numpy_input(self):
    # In addition to Tensors, we also support raw numpy arrays as inputs.
    r = np.random.RandomState(0)
    s = 'ijk,ijl,ikl->i'
    x = r.randn(1, 2, 3)
    y = r.randn(1, 2, 4)
    z = r.randn(1, 3, 4)

    a = np.einsum(s, x, y, z)
    b = self.evaluate(special_math_ops.einsum(s, x, y, z))
    self.assertAllClose(a, b, atol=1e-4, rtol=1e-4)

  def test_long_cases(self):
    cases = [
        'efc,dbc,acf,fd->abe',
        'ea,fb,gc,hd,abcd->efgh',
        'abhe,hidj,jgba,hiab,gab->ed',
        # Cases with whitespace.
        'efc, dbc, acf, fd -> abe',
        'abhe, hidj, jgba, hiab, gab',
        # Repeated equations for cache hit on the opt_einsum call.
        'ea,fb,abcd,gc,hd->efgh',
        'ea,fb,abcd,gc,hd->efgh',
    ]
    dimension_map = dict((c, ord(c) - ord('a') + 1) for c in 'abcdefghij')
    for equation in cases:
      inputs = equation.split('->')[0].replace(' ', '')
      input_shapes = []
      for input_str in inputs.split(','):
        input_shapes.append(tuple([dimension_map[c] for c in input_str]))
      self._check(equation, *input_shapes)

  def test_opt_einsum_cached(self):
    # Checks call_count to opt_einsum which are only reflected in eager mode.
    if not context.executing_eagerly():
      return

    input_1 = ('ijk,ijl,ikl->i', (1, 2, 3), (1, 2, 4), (1, 3, 4))
    input_2 = ('ij,ij,jk,kl->il', (1, 2), (1, 2), (2, 3), (3, 4))

    with test.mock.patch.object(
        opt_einsum, 'contract_path',
        wraps=opt_einsum.contract_path) as mock_contract_path:

      # explicitly clear the lru_cache contents for the method
      #   special_math_ops.get_opt_einsum_contract_path
      # We need to do this because other tests in this file invoke that method
      # with the same input args (as input_1 and input_2 above), and if
      # those tests run before this test, then the call_count for the method
      # mock_contract_path will not increment.
      if six.PY3:
        special_math_ops._get_opt_einsum_contract_path.cache_clear()

      self.assertEqual(mock_contract_path.call_count, 0)
      self._check(*input_1)
      self.assertEqual(mock_contract_path.call_count, 1)
      # The same input results in no extra call if we're caching the
      # opt_einsum.contract_path call. We only cache in Python3.
      self._check(*input_1)
      self.assertEqual(mock_contract_path.call_count, 1 if six.PY3 else 2)
      # New input results in another call to opt_einsum.
      self._check(*input_2)
      self.assertEqual(mock_contract_path.call_count, 2 if six.PY3 else 3)
      # No more extra calls as the inputs should be cached.
      self._check(*input_1)
      self._check(*input_2)
      self._check(*input_1)
      self.assertEqual(mock_contract_path.call_count, 2 if six.PY3 else 6)

  @test_util.disable_xla('b/131919749')
  def test_long_cases_with_repeated_labels(self):
    cases = [
        # Tests from dask.
        'fdf,cdd,ccd,afe->ae',
        'fff,fae,bef,def->abd',
    ]
    dimension_map = dict((c, ord(c) - ord('a') + 1) for c in 'abcdefghij')
    for equation in cases:
      inputs = equation.split('->')[0].replace(' ', '')
      input_shapes = []
      for input_str in inputs.split(','):
        input_shapes.append(tuple([dimension_map[c] for c in input_str]))
      self._check(equation, *input_shapes)

  @test_util.disable_xla('b/131919749')
  @test_util.run_in_graph_and_eager_modes
  def test_invalid_equation(self):
    r = np.random.RandomState(0)
    cases = [
        # invalid equation format.
        ('a0->a', r.randn(5, 3)),
        ('a->a,a', r.randn(5)),
        ('a->a->a', r.randn(5)),
        ('ijk ijk', r.randn(1, 2, 3), r.randn(1, 2, 3)),
        ('ij.jk->ik', r.randn(2, 3), r.randn(3, 4)),
        # output label not present in input.
        ('a->b', r.randn(5)),
        ('ij,jk->im', r.randn(2, 3), r.randn(3, 4)),
        # wrong shape.
        ('ij,jk->ik', r.randn(1, 2, 3), r.randn(3, 4)),
        # inconsistent dimensions.
        ('ij,jk->ik', r.randn(2, 3), r.randn(4, 4)),
        # output has repeated subscripts.
        ('ij,jk->iik', r.randn(2, 3), r.randn(3, 4)),
        # too many ellipses
        ('...ij...,jk...->ik...', r.randn(2, 3), r.randn(3, 4)),
        ('...ij,jk...->...ik...', r.randn(2, 3), r.randn(3, 4)),
        # invalid broadcast dimensions.
        ('...ij,...jk->...ik', r.randn(5, 2, 3), r.randn(7, 3, 4)),
        # output should have ellipsis when broadcasting shape is non-empty.
        ('...ij,...jk->ik', r.randn(2, 2, 3), r.randn(3, 4)),
    ]
    for args in cases:
      with self.assertRaises((ValueError, errors.InvalidArgumentError)):
        _ = special_math_ops.einsum(*args)

      placeholders = [
          array_ops.placeholder_with_default(x, shape=None) for x in args[1:]
      ]
      with self.assertRaises((ValueError, errors.InvalidArgumentError)):
        _ = self.evaluate(special_math_ops.einsum(args[0], *placeholders))

  @test_util.disable_xla('b/131919749')
  def test_empty(self):

    def check(equation, input_shapes, output_shape):
      # All these cases result in an output filled with zeros, so we don't call
      # np.einsum. Also np.einsum doesn't support generalized diagonals which
      # are needed for EinsumOp gradients.
      r = np.random.RandomState(0)
      inputs = [np.array(r.randn(*shape)) for shape in input_shapes]
      input_tensors = [constant_op.constant(x, shape=x.shape) for x in inputs]
      output = self.evaluate(special_math_ops.einsum(equation, *input_tensors))
      self.assertAllClose(output, np.zeros(output_shape), atol=1e-4, rtol=1e-4)

    # Contractions along zero-sized dimensons.
    check('ab,bc->ac', [(0, 10), (10, 10)], (0, 10))
    # From transformer xl.
    check('ibnd,ijbn->jnd', [(1, 0, 5, 10), (1, 1, 0, 5)], (1, 5, 10))

    # Generalized traces with zero-sized dimensions.
    check('aab,bc->ac', [(0, 0, 10), (10, 10)], (0, 10))
    check('aaab,bc->c', [(0, 0, 0, 3), (3, 4)], (4,))


@test_util.run_all_in_graph_and_eager_modes
class EinsumGradTest(test.TestCase):

  def _check_gradient(self, s, *input_shapes):
    with self.cached_session():
      r = np.random.RandomState(0)
      inputs = [np.array(r.randn(*shape)) for shape in input_shapes]
      input_tensors = [constant_op.constant(x, shape=x.shape) for x in inputs]
      analytical, numerical = gradient_checker_v2.compute_gradient(
          lambda *xs: special_math_ops.einsum(s, *xs), input_tensors)
      self.assertLess(
          gradient_checker_v2.max_error(analytical, numerical), 1e-4)

  @test_util.disable_xla('b/131919749')
  def test_unary(self):
    self._check_gradient('->', ())
    self._check_gradient('aaa->a', (3, 3, 3))
    self._check_gradient('aabcd->ad', (3, 3, 5, 4, 4))
    self._check_gradient('abcd->da', (3, 5, 4, 2))

  @test_util.disable_xla('b/131919749')
  def test_unary_ellipsis(self):
    self._check_gradient('...->...', ())
    self._check_gradient('...->', ())
    self._check_gradient('->...', ())

    # Tests from dask
    self._check_gradient('a...a->a...', (2, 2))
    self._check_gradient('a...a->', (2, 2))
    self._check_gradient('a...a->...', (2, 5, 1, 2))
    self._check_gradient('a...a->a...', (2, 1, 2))
    self._check_gradient('a...a->a...', (2, 3, 4, 5, 2))

    self._check_gradient('...ijk->...ki', (3, 4, 5))
    self._check_gradient('...ijk->...ki', (1, 3, 4, 5))
    self._check_gradient('...ijk->...ki', (2, 2, 3, 4, 5))
    self._check_gradient('ab...cd->da...', (3, 5, 2, 3, 4, 2))

  def test_binary_simple(self):
    # Binary cases in XLA mode must have either (a) each index appearing
    # exactly once in both the inputs (batch or contraction index), or
    # (b) appearing exactly once in an input and in the output (free index).
    self._check_gradient(',->', (), ())
    self._check_gradient('a,a->', (3,), (3,))
    self._check_gradient('a,a->a', (3,), (3,))
    self._check_gradient('ab,b->a', (3, 4), (4,))
    self._check_gradient('ab,ab->', (3, 4), (3, 4))
    self._check_gradient('ab,bc->ac', (3, 4), (4, 5))
    self._check_gradient('nij,jk->nik', (5, 2, 3), (3, 4))
    self._check_gradient('abc,bad->abcd', (1, 2, 3), (2, 1, 4))
    # Based on https://github.com/google/jax/issues/37#issuecomment-448572187
    self._check_gradient('sa,shb->shab', (2, 1), (2, 3, 4))

  def test_empty(self):
    # From Transformer XL.
    self._check_gradient('ibnd,ijbn->jnd', (1, 0, 5, 10), (1, 1, 0, 5))

  @test_util.disable_xla('b/131919749')
  def test_reduced_indices(self):
    self._check_gradient('ba,b->', (3, 2), (3,))
    self._check_gradient('ab,ab->', (3, 4), (3, 4))
    self._check_gradient('abce,badf->abcd', (1, 2, 3, 4), (2, 1, 4, 3))

  @test_util.disable_xla('b/131919749')
  def test_repeated_indices(self):
    # Repeated indices.
    self._check_gradient('aba,a->b', (3, 4, 3), (3,))
    self._check_gradient('ijj,k->ik', (2, 3, 3), (4,))
    self._check_gradient('ill,k->ik', (2, 3, 3), (4,))
    # From https://github.com/dask/dask/pull/3412#discussion_r182413444
    self._check_gradient('aab,bc->ac', (1, 1, 3), (3, 4))
    self._check_gradient('aab,bcc->ac', (2, 2, 3), (3, 4, 4))

  @test_util.disable_xla('b/131919749')
  def test_empty_with_repeated_indices(self):
    self._check_gradient('aab,bc->ac', (0, 0, 10), (10, 10))
    self._check_gradient('aab,bc->ac', (1, 1, 0), (0, 10))
    self._check_gradient('aaab,bc->c', (0, 0, 0, 3), (3, 4))

  @test_util.disable_xla('b/131919749')
  def test_broadcasting(self):
    self._check_gradient('...ij,...jk->...ik', (3, 2), (2, 4))
    self._check_gradient('ij...,jk...->ik...', (3, 2, 1), (2, 4))
    self._check_gradient('...ij,...jk->...ik', (3, 1, 3, 2), (1, 5, 2, 4))
    self._check_gradient('ij,jk...k->i...', (3, 2), (2, 4, 1, 4))
    self._check_gradient('aab,b...c->a...c', (1, 1, 3), (3, 1, 1, 4))
    # Tests from dask.
    self._check_gradient('...i,...j,...k->...ijk', (1, 4, 1, 2), (5, 1, 1, 3),
                         (1, 1, 1, 1, 9))
    self._check_gradient('...i,...j,...k->...ijk', (1,), (1,), (1,))

  def test_long_cases(self):
    cases = [
        'abhe,hidj,jgba,hiab,gab->ed',
        # Tests from dask.
        'ea,fb,abcd,gc,hd->efgh',
    ]
    dimension_map = dict(
        (c, ((ord(c) - ord('a')) % 3) + 1) for c in 'abcdefghij')
    for equation in cases:
      inputs = equation.split('->')[0].replace(' ', '')
      input_shapes = []
      for input_str in inputs.split(','):
        input_shapes.append(tuple([dimension_map[c] for c in input_str]))
      self._check_gradient(equation, *input_shapes)

  @test_util.disable_xla('b/131919749')
  def test_long_cases_with_repeated_labels(self):
    cases = [
        # Tests from dask.
        'fdf,cdd,ccd,afe->ae',
        'fff,fae,bef,def->abd',
    ]
    dimension_map = dict(
        (c, ((ord(c) - ord('a')) % 3) + 1) for c in 'abcdefghij')
    for equation in cases:
      inputs = equation.split('->')[0].replace(' ', '')
      input_shapes = []
      for input_str in inputs.split(','):
        input_shapes.append(tuple([dimension_map[c] for c in input_str]))
      self._check_gradient(equation, *input_shapes)


class EinsumBenchmark(test.Benchmark):
  cases = [
      # Unary cases.
      ['ijk->i', 100],
      ['ijk->kji', 100],
      # Regular matmul or batch matmul.
      ['ij,jk->ik', 500],
      ['ji,kj->ik', 500],
      ['bij,bjk->bik', 100],
      ['bji,bjk->bki', 100],
      ['ikl,kji->kl', 100],
      ['klj,lki->ij', 100],
      ['ijk,ilj->kli', 100],
      ['ijk,jklm->il', 50],
      # Larger binary contractions.
      ['efabc,eabcd->efd', 20],
      ['fabec,abcde->fde', 20],
      ['efabc,edabc->efd', 20],
      ['eadbf,dfebc->ecfad', 20],
      ['abcdef,bcdfg->abcdeg', 20],
      # Chain matmul.
      ['ij,jk,kl->il', 1000],
      # Long cases. Path optimization should kick in.
      ['ea,fb,abcd,gc,hd->efgh', 10],
      ['bca,cdb,dbf,afc->', 10],
      ['efc,dbc,acf,fd->abe', 10],
      ['abhe,hidj,jgba,hiab,gab->ed', 10],
  ]

  def benchmark_einsum(self):
    for equation, dim in self.cases:
      with ops.Graph().as_default(), \
          session.Session(config=benchmark.benchmark_config()) as sess, \
          ops.device('/cpu:0'):
        r = np.random.RandomState(0)
        input_subscripts = equation.split('->')[0].split(',')
        input_vars = []
        for subscript in input_subscripts:
          input_shape = (dim,) * len(subscript)
          input_vars.append(
              variables.Variable(np.array(r.randn(*input_shape), np.float32)))
        variables.global_variables_initializer().run()

        if len(input_vars) <= 2:
          self.run_op_benchmark(
              sess,
              special_math_ops.einsum(equation, *input_vars),
              min_iters=50,
              name='einsum_cpu_({})_{}'.format(equation, dim))
        else:
          for optimize in ['greedy', 'auto']:
            self.run_op_benchmark(
                sess,
                special_math_ops.einsum(
                    equation, *input_vars, optimize=optimize),
                min_iters=50,
                name='einsum_cpu_({})_{}_{}'.format(equation, optimize, dim))


if __name__ == '__main__':
  test.main()
