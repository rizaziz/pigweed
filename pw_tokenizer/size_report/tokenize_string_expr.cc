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

#include "base.h"

// Data to be included in size report.
static struct TokenizeStringExprContainer : BaseContainer {
#ifdef BASELINE
  uint32_t token = 1234;
#else   // BASELINE
  uint32_t token = PW_TOKENIZE_STRING_EXPR("token");
#endif  // BASELINE

  virtual long LoadData() override { return BaseContainer::LoadData() ^ token; }
} size_report_data;

int main() {
  // Load size report data.
  return size_report_data.LoadData();
}