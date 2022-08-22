# Copyright 2022 The Pigweed Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
"""Module for size report ASCII tables from DataSourceMaps."""

import enum
from typing import (Iterable, Tuple, Union, Type, List, Optional, NamedTuple,
                    cast)

from pw_bloat.label import DataSourceMap, DiffDataSourceMap, Label


class AsciiCharset(enum.Enum):
    """Set of ASCII characters for drawing tables."""
    TL = '+'
    TM = '+'
    TR = '+'
    ML = '+'
    MM = '+'
    MR = '+'
    BL = '+'
    BM = '+'
    BR = '+'
    V = '|'
    H = '-'
    HH = '='


class LineCharset(enum.Enum):
    """Set of line-drawing characters for tables."""
    TL = '┌'
    TM = '┬'
    TR = '┐'
    ML = '├'
    MM = '┼'
    MR = '┤'
    BL = '└'
    BM = '┴'
    BR = '┘'
    V = '│'
    H = '─'
    HH = '═'


class _Align(enum.Enum):
    CENTER = 0
    LEFT = 1
    RIGHT = 2


class BloatTableOutput:
    """ASCII Table generator from DataSourceMap."""

    _RST_PADDING_WIDTH = 6

    class _LabelContent(NamedTuple):
        name: str
        size: int
        label_status: str

    def __init__(self,
                 ds_map: Union[DiffDataSourceMap, DataSourceMap],
                 col_max_width: int,
                 charset: Union[Type[AsciiCharset],
                                Type[LineCharset]] = AsciiCharset,
                 rst_output: bool = False):
        self._data_source_map = ds_map
        self._cs = charset
        self._total_size = 0
        col_names = [*self._data_source_map.get_ds_names(), 'sizes']
        self._diff_mode = False
        if isinstance(self._data_source_map, DiffDataSourceMap):
            col_names = ['diff', *col_names]
            self._diff_mode = True
        self._col_names = col_names
        self._additional_padding = 0
        self._ascii_table_rows: List[str] = []
        self._rst_output = rst_output
        self._total_divider = self._cs.HH.value
        if self._rst_output:
            self._total_divider = self._cs.H.value
            self._additional_padding = self._RST_PADDING_WIDTH

        self._col_widths = self._generate_col_width(col_max_width)

    def _diff_sign_sizes(self, size: int) -> str:
        if self._diff_mode:
            size_sign = '+' if size > 0 else ''
            return f"{size_sign}{size:,}"
        return f"{size:,}"

    def _generate_col_width(self, col_max_width: int) -> List[int]:
        """Find column width for all data sources and sizes."""
        col_list = [
            len(ds_name) for ds_name in self._data_source_map.get_ds_names()
        ]
        for curr_label in self._data_source_map.labels():
            self._total_size += curr_label.size
            for index, parent_label in enumerate(
                [*curr_label.parents, curr_label.name]):
                if len(parent_label) > col_max_width:
                    col_list[index] = col_max_width
                elif len(parent_label) > col_list[index]:
                    col_list[index] = len(parent_label)

        diff_same = 0
        if self._diff_mode:
            col_list = [len('Total'), *col_list]
            diff_same = len('(SAME)')
        col_list.append(
            max(len(self._diff_sign_sizes(self._total_size)), len('sizes'),
                diff_same))

        return [x + self._additional_padding for x in col_list]

    def _diff_label_names(
            self, old_labels: Optional[Tuple[_LabelContent, ...]],
            new_labels: Tuple[_LabelContent,
                              ...]) -> Tuple[_LabelContent, ...]:
        """Return difference between arrays of labels."""

        if old_labels is None:
            return new_labels
        diff_list = []
        for (new_lb, old_lb) in zip(new_labels, old_labels):
            if (new_lb.name == old_lb.name) and (new_lb.size == old_lb.size):
                diff_list.append(self._LabelContent('', 0, ''))
            else:
                diff_list.append(new_lb)

        return tuple(diff_list)

    def create_table(self) -> str:
        """Parse DataSourceMap to create ASCII table."""
        curr_lb_hierachy = None
        last_diff_name = ''
        self._ascii_table_rows.extend([*self.create_title_row()])
        for curr_label in self._data_source_map.labels():
            new_lb_hierachy = tuple([
                *self.get_ds_label_size(curr_label.parents),
                self._LabelContent(curr_label.name, curr_label.size,
                                   self.get_label_status(curr_label))
            ])
            diff_list = self._diff_label_names(curr_lb_hierachy,
                                               new_lb_hierachy)
            curr_lb_hierachy = new_lb_hierachy
            if curr_label.parents[0] == last_diff_name:
                continue
            if self._diff_mode and diff_list[0].name and (not cast(
                    DiffDataSourceMap,
                    self._data_source_map).has_diff_sublabels(
                        diff_list[0].name)):
                if len(self._ascii_table_rows) > 3 and (not self._rst_output):
                    self._ascii_table_rows.append(
                        self.row_divider(len(self._col_names),
                                         self._cs.H.value))
                self._ascii_table_rows.append(
                    self.create_same_label_row(1, diff_list[0].name))

                last_diff_name = curr_label.parents[0]
            else:
                self._ascii_table_rows += self.create_rows_diffs(diff_list)

        if self._rst_output and self._ascii_table_rows[-1][0] == '+':
            self._ascii_table_rows.pop()

        self._ascii_table_rows.extend([*self.create_total_row()])

        return '\n'.join(self._ascii_table_rows)

    def create_same_label_row(self, col_index: int, label: str) -> str:
        label_row = ''
        for col in range(len(self._col_names) - 1):
            if col == col_index:
                curr_cell = self.create_cell(label, False, col, _Align.LEFT)
            else:
                curr_cell = self.create_cell('', False, col)
            label_row += curr_cell
        label_row += self.create_cell("(SAME)", True,
                                      len(self._col_widths) - 1, _Align.RIGHT)
        return label_row

    def get_ds_label_size(
            self, parent_labels: Tuple[str, ...]) -> Iterable[_LabelContent]:
        """Produce label, size pairs from parent label names."""
        parent_label_sizes = []
        for index, target_label in enumerate(parent_labels):
            for curr_label in self._data_source_map.labels(index):
                if curr_label.name == target_label:
                    diff_label = self.get_label_status(curr_label)
                    parent_label_sizes.append(
                        self._LabelContent(curr_label.name, curr_label.size,
                                           diff_label))
                    break
        return parent_label_sizes

    def create_total_row(self) -> Iterable[str]:
        complete_total_rows = []
        complete_total_rows.append(
            self.row_divider(len(self._col_names), self._total_divider))
        total_row = ''
        for i in range(len(self._col_names)):
            if i == 0:
                total_row += self.create_cell('Total', False, i, _Align.LEFT)
            elif i == len(self._col_names) - 1:
                total_size_str = self._diff_sign_sizes(self._total_size)
                total_row += self.create_cell(total_size_str, True, i)
            else:
                total_row += self.create_cell('', False, i, _Align.CENTER)

        complete_total_rows.extend(
            [total_row, self.create_border(False, self._cs.H.value)])
        return complete_total_rows

    def create_rows_diffs(
            self, diff_list: Tuple[_LabelContent, ...]) -> Iterable[str]:
        """Create rows for each label according to its index in diff_list."""
        curr_row = ''
        diff_index = 0
        diff_rows = []
        for index, label_content in enumerate(diff_list):
            if label_content.name:
                if self._diff_mode:
                    curr_row += self.create_cell(label_content.label_status,
                                                 False, 0)
                    diff_index = 1
                for cell_index in range(diff_index,
                                        len(diff_list) + diff_index):
                    if cell_index == index + diff_index:
                        if cell_index == diff_index and len(
                                self._ascii_table_rows
                        ) > 3 and not self._rst_output:
                            diff_rows.append(
                                self.row_divider(len(self._col_names),
                                                 self._cs.H.value))
                        if (len(label_content.name) + self._additional_padding
                            ) > self._col_widths[cell_index]:
                            curr_row = self.multi_row_label(
                                label_content.name, cell_index)
                            break
                        curr_row += self.create_cell(label_content.name, False,
                                                     cell_index, _Align.LEFT)
                    else:
                        curr_row += self.create_cell('', False, cell_index)

                #Add size end of current row.
                curr_size = self._diff_sign_sizes(label_content.size)
                curr_row += self.create_cell(curr_size, True,
                                             len(self._col_widths) - 1,
                                             _Align.RIGHT)
                diff_rows.append(curr_row)
                if self._rst_output:
                    diff_rows.append(
                        self.row_divider(len(self._col_names),
                                         self._cs.H.value))
                curr_row = ''

        return diff_rows

    def create_cell(self,
                    content: str,
                    last_cell: bool,
                    col_index: int,
                    align: Optional[_Align] = _Align.RIGHT) -> str:
        v_border = self._cs.V.value
        if self._rst_output and content:
            content = f" ``{content}`` "
        pad_diff = self._col_widths[col_index] - len(content)
        padding = (pad_diff // 2) * ' '
        odd_pad = ' ' if pad_diff % 2 == 1 else ''
        string_cell = ''

        if align == _Align.CENTER:
            string_cell = f"{v_border}{odd_pad}{padding}{content}{padding}"
        elif align == _Align.LEFT:
            string_cell = f"{v_border}{content}{padding*2}{odd_pad}"
        elif align == _Align.RIGHT:
            string_cell = f"{v_border}{padding*2}{odd_pad}{content}"

        if last_cell:
            string_cell += self._cs.V.value
        return string_cell

    def multi_row_label(self, content: str, target_col_index: int) -> str:
        """Split content name into multiple rows within correct column."""
        max_len = self._col_widths[target_col_index] - self._additional_padding
        split_content = '...'.join(
            content[max_len:][i:i + max_len - 3]
            for i in range(0, len(content[max_len:]), max_len - 3))
        split_content = f"{content[:max_len]}...{split_content}"
        split_tab_content = [
            split_content[i:i + max_len]
            for i in range(0, len(split_content), max_len)
        ]
        multi_label = []
        curr_row = ''
        for index, cut_content in enumerate(split_tab_content):
            last_cell = False
            for blank_cell_index in range(len(self._col_names)):
                if blank_cell_index == target_col_index:
                    curr_row += self.create_cell(cut_content, False,
                                                 target_col_index, _Align.LEFT)
                else:
                    if blank_cell_index == len(self._col_names) - 1:
                        if index == len(split_tab_content) - 1:
                            break
                        last_cell = True
                    curr_row += self.create_cell('', last_cell,
                                                 blank_cell_index)
            multi_label.append(curr_row)
            curr_row = ''

        return '\n'.join(multi_label)

    def row_divider(self, col_num: int, h_div: str) -> str:
        l_border = ''
        r_border = ''
        row_div = ''
        for col in range(col_num):
            if col == 0:
                l_border = self._cs.ML.value
                r_border = ''
            elif col == (col_num - 1):
                l_border = self._cs.MM.value
                r_border = self._cs.MR.value
            else:
                l_border = self._cs.MM.value
                r_border = ''

            row_div += f"{l_border}{self._col_widths[col] * h_div}{r_border}"
        return row_div

    def create_title_row(self) -> Iterable[str]:
        title_rows = []
        title_cells = ''
        last_cell = False
        for index, name in enumerate(self._col_names):
            if index == len(self._col_names) - 1:
                last_cell = True
            title_cells += self.create_cell(name, last_cell, index,
                                            _Align.CENTER)
        title_rows.extend([
            self.create_border(True, self._cs.H.value), title_cells,
            self.row_divider(len(self._col_names), self._cs.HH.value)
        ])
        return title_rows

    def create_border(self, top: bool, h_div: str):
        """Top or bottom borders of ASCII table."""
        row_div = ''
        for col in range(len(self._col_names)):
            if top:
                if col == 0:
                    l_div = self._cs.TL.value
                    r_div = ''
                elif col == (len(self._col_names) - 1):
                    l_div = self._cs.TM.value
                    r_div = self._cs.TR.value
                else:
                    l_div = self._cs.TM.value
                    r_div = ''
            else:
                if col == 0:
                    l_div = self._cs.BL.value
                    r_div = ''
                elif col == (len(self._col_names) - 1):
                    l_div = self._cs.BM.value
                    r_div = self._cs.BR.value
                else:
                    l_div = self._cs.BM.value
                    r_div = ''

            row_div += f"{l_div}{self._col_widths[col] * h_div}{r_div}"
        return row_div

    @staticmethod
    def get_label_status(curr_label: Label) -> str:
        if curr_label.is_new():
            return '++'
        if curr_label.is_del():
            return '--'
        return ''


class RstOutput(BloatTableOutput):
    """Tabular output in ASCII format, which is also valid RST."""
    def __init__(self, ds_map: DataSourceMap, col_width: int):
        super().__init__(ds_map, col_width, AsciiCharset, rst_output=True)

    def create_table(self) -> str:
        """RST tables requires a newline after table."""
        return super().create_table() + '\n'