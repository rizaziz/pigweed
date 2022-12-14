// Copyright 2022 The Pigweed Authors
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not
// use this file except in compliance with the License. You may obtain a copy of
// the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
// WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
// License for the specific language governing permissions and limitations under
// the License.
#pragma once

#include <mutex>

namespace pw::sync::backend {

// The NativeRecursiveMutex class adds a flag that tracks how many times the
// std::recursive_mutex has been locked. The C++ standard states that misusing a
// mutex is undefined behavior, so library implementations may simply ignore
// misuse. This ensures misuse hits a PW_ASSERT.
struct NativeRecursiveMutex {
  std::recursive_mutex mutex;
  unsigned lock_count = 0;
};

using NativeRecursiveMutexHandle = std::recursive_mutex&;

}  // namespace pw::sync::backend
