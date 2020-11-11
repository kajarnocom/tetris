#!/usr/bin/env python
# -*- coding: latin-1 -*-

"""
Create hierarchical .svg Voronoi tree graphs like GrandPerspective on Mac
"""

import pandas as pd
import numpy as np
import kajsvg
import kajlib as lib
import sys
import os

def tree_paint(input_spreadsheet, input_sheet, levels, area, quality, borders):
    # Prepare SVG canvas
    svg.set_canvas("A4")
    svg.set_orientation("portrait")
    svg.reset_margins()
    svg.def_margins('outer', 'mm', 15, 13, 15, 8)
    svg.def_margins('inner', 'mm', 30, 19, 21, 14)
    svg.set_margins()
    svg.set_title(f"Tetris Tree / Voronoi Diagram for {input_sheet}", "tetris.py")
    s = svg.doc_header()
    s += svg.comment(f"Parameters: Levels {levels} Area {area} Quality {quality} Borders {borders}")
    s += svg.comment(f"Margins: {svg.margins}")
    s += svg.comment(f"Canvas: {svg.canvas}")

    #scale = 1 - 81. / 175
    scale = 1
    margin = 5
    height = 68 * scale

    x0 = margin
    x1 = 205
    y0 = margin
    y1 = y0 + height

    df = pd.read_excel(input_spreadsheet, sheet_name=input_sheet)
    df = df.replace(np.nan, '', regex=True)

    # Check that all applicable fields exist
    skip = False
    if not area in df.columns:
        print(f"tetris.py: missing area column '{area}' in {input_spreadsheet} tab {input_sheet}")
        skip = True
    if not quality in df.columns:
        print(f"tetris.py: missing quality column '{quality}' in {input_spreadsheet} tab {input_sheet}")
        skip = True
    for field in levels:
        if not field in df.columns:
            print(f"tetris.py: missing levels column '{field}' in {input_spreadsheet} tab {input_sheet}")
            skip = True
    if skip:
        print("- skipping this row")
        return ""

    current_level = []
    for item in levels:
        current_level.append(item)
        cols = levels + [area, quality]
        #print(f"current_level {current_level} cols {cols}")
        s += svg.comment(f"Level {current_level}, cols {cols}")
        data2 = df[cols]
        data = data2.set_index(levels)
        level_slash = "/".join(current_level)
        sys.stdout.write(f"\n{level_slash}: ")
        s += split_into_subtrees(data, current_level, 1, x0, y0, x1, y1, item, area, quality, borders)
        y0 += margin + height
        y1 += margin + height
    s += "</svg>"
    return s

def split_into_subtrees(data, levels, level, x0, y0, x1, y1, text_field, area, quality, borders):
    #print(f"split_into_subtrees(data,�{levels} level {level}, x0 {x0:5.2f}, y0 {y0:5.2f}, x0 {x1:5.2f}, y1 {y1:5.2f}, {text_field})")
    sys.stdout.write(str(level))
    sys.stdout.flush()
    rows = len(data.index)
    #print(f"rows {rows}")
    if rows == 0: # We have "split" a chunk of only one row into two chunks,
        # the second of which is obviously empty
        return ""
    #print(f"Level {level} len(levels) {len(levels)} rows {rows}")
    if rows == 1: # Now we have reached the bottom and can paint
        return paint_cell(data, x0, y0, x1, y1, text_field, area, quality, borders)
    if level == len(levels) + 1: # Maximum desired level of recursion
        return paint_cell(data, x0, y0, x1, y1, text_field, area, quality, borders)

    # The splitting algorithm may have de-sorted the data
    #data_index = data.set_index(levels)
    data_sorted = data.sort_index()
    #print(f"levels {levels} index {data_sorted.index}")
    #print(f"depth {data_sorted.index.lexsort_depth}")

    # Go one level deeper, if only one entry on this level
    current_level = levels[0:level]
    EntriesOnThisLevel = len(data_sorted.groupby(current_level).size().index)
    if EntriesOnThisLevel == 1:
        level += 1
        current_level = levels[0:level]

    # Sort the entries on this level by size, descending order
    chunksizes = []
    for name, group in data.groupby(current_level)[area]:
        chunksizes += [(group.sum(), name)]
    sorted_chunks = sorted(chunksizes, key = lambda x: x[0], reverse=True)
    #print(f"EntriesOnThisLevel {EntriesOnThisLevel}, Chunksizes {chunksizes}")

    # Separate the entries into two chunks, as equal in size as can be
    data_1 = pd.DataFrame()
    data_2 = pd.DataFrame()
    tree_1_size = tree_2_size = 0
    s = ""
    for chunk in sorted_chunks:
        id = chunk[1]
        #print(f"typeof id {type(id)}")
        size = chunk[0]
        this_data = data_sorted[id:id]  # todo Denna blir tom d� id = en m�nad!
        #print(f"id {id} size {size} tree 1 size {tree_1_size} len {len(data_1.index)} tree 2 size {tree_2_size} len {len(data_2.index)} this_data {this_data}")
        #      f"�data_sorted {data_sorted}")
        if tree_1_size <= tree_2_size:
            tree_1_size += size
            data_1 = pd.concat([data_1, this_data])
        else:
            tree_2_size += size
            data_2 = pd.concat([data_2, this_data])

    # Now recursively split both of the two chunks
    first_share = tree_1_size / (tree_1_size + tree_2_size)
    aspect_ratio = (y1 - y0) / (x1 - x0)
    IsPortrait = aspect_ratio > 1
    if IsPortrait:
        y_mid = y0 + first_share * (y1 - y0)
        if tree_1_size > 0:
            s = split_into_subtrees(data_1, levels, level, x0, y0, x1, y_mid, text_field, area, quality, borders)
        if tree_2_size > 0:
            s += split_into_subtrees(data_2, levels, level, x0, y_mid, x1, y1, text_field, area, quality, borders)
    else:
        x_mid = x0 + first_share * (x1 - x0)
        if tree_1_size > 0:
            s = split_into_subtrees(data_1, levels, level, x0, y0, x_mid, y1, text_field, area, quality, borders)
        if tree_2_size > 0:
            s += split_into_subtrees(data_2, levels, level, x_mid, y0, x1, y1, text_field, area, quality, borders)
    return s

def paint_cell(data, x0, y0, x1, y1, text_field, area, quality, borders):

    # Find out colour of cell
    row = data.reset_index()
    quality_val = float(row[quality].mean())
    fg_color = "black"
    bg_color = borders[-1]["bg_color"]
    for limit_dict in borders:
        rule = limit_dict['rule']
        # last line is an "else" catch-up clause, if the value is empty
        if rule == "":
            break
        pot_bg_color = limit_dict["bg_color"]
        pot_fg_color = limit_dict["fg_color"]
        condition = rule[0]
        value = float(rule[1:])
        match = False
        if condition == ">":
            if quality_val > value:
                match = True
        elif condition == "=":
            if quality_val == value:
                match = True
        elif condition == "<":
            if quality_val < value:
                match = True
        #print(f"pot_bg {pot_bg_color} border {border} quality {quality_val} value {value} match {match}")
        if match:
            bg_color = pot_bg_color
            if pot_fg_color != "":
                fg_color = pot_fg_color
            break
    #print(f"quality_val {quality_val} condition {condition} value {value} bg_color {bg_color} pot {pot_bg_color}")

    fill_style = {'fill': bg_color}
    s = svg.plot_rect_mm(x0, y0, x1 - x0, y1 - y0, fill_style)

    # Find out text to write in cell
    text = row[text_field].min()
    available_width = x1 - x0
    available_height = y1 - y0
    is_portrait = available_height > available_width
    angle = (-90 if is_portrait else 0)
    max_point_size = 0.9 * (available_width if is_portrait else available_height)
    text = str(text)
    text_width = len(text)
    ratio = max(available_width / text_width, available_height / text_width)
    text_size = min(max_point_size, min(24, 0.1 * int(14 * ratio)))

    text_style = {'font-size': text_size, 'text-anchor': "middle", 'dominant-baseline': "central", 'fill': fg_color}
    s += svg.comment(f"{text}: max_point_size {max_point_size:.2f} textsize {text_size}")
    #s += svg.comment(f"- {text}: ratio {ratio:.2f} available width {available_width:.2f}")
    s += svg.plot_text_mm(x0 + available_width / 2, y0 + available_height / 2, text, text_style, angle=angle)
    #print(text)
    #row2 = row.values[0].astype(str)
    #row3 = map(str, row2)
    #row4 = ' '.join(row3)
    #print(f"bottom {row4} - ({x0:.2f}, {y0:.2f}) - ({x1:.2f}, {y1:.2f})")
    return s

# Identify right input file
parameter_given = len(sys.argv) > 1
if parameter_given:
    input_spreadsheet = sys.argv[1]
else:
    input_spreadsheet = "tetris.xlsx"

# Verify that the input file exists
if not os.path.exists(input_spreadsheet):
    print(f"tetris.py error: Could not find input file {input_spreadsheet} (cwd = {os.getcwd()})")
    sys.exit(0)
else:
    print(f"tetris.py: Opening {input_spreadsheet} (cwd = {os.getcwd()})")

# Verify that the Commands sheet exists
xl = pd.ExcelFile(input_spreadsheet)
sheet_names = xl.sheet_names
if not "Commands" in sheet_names:
    print(f"tetris.py error: Could not find sheet 'Commands' in file {input_spreadsheet}")
    sys.exit(0)

cmds = pd.read_excel(input_spreadsheet, sheet_name='Commands')
cmds = cmds.replace(np.nan, '', regex=True)

for index, row in cmds.iterrows():
    active = row['active']
    input_sheet = row['input_sheet']
    if active == "#": # Commented out line, not to be executed
        continue
    output_svgfile = row['output_svgfile'] + ".svg"
    levelstr = row['levels']
    levels = levelstr.replace(" ", "").split(",")
    area = row['area']
    quality = row['quality']
    color_sheet = row['color_sheet']
    borders = []
    for i in range(1, 7):
        rule = row['rule' + str(i)]
        bg_color = row['bg_color' + str(i)]
        fg_color = row['fg_color' + str(i)]
        if bg_color != "":
            borders.append({"rule": rule, "bg_color": bg_color, "fg_color": fg_color})
    slash_levels = "/".join(levels)
    print(f"\n{index}. {input_sheet} --> {output_svgfile}: {slash_levels} Area: {area} Quality: {quality}")

    if not color_sheet in sheet_names:
        print(f"tetris.py error: Could not find color_sheet '{color_sheet}' in file {input_spreadsheet} (row = {input_sheet})")
        print("- Skipping this row")
        continue

    colors = pd.read_excel(input_spreadsheet, sheet_name=color_sheet)
    _colors ={}
    for i, r in colors.iterrows():
        c1 = r['color']
        c2 = r['pf_color']
        hex = r['hex']
        _colors[c1] = hex
        _colors[c2] = hex
    svg = kajsvg.SVG(_colors)

    # Check that input datasheet exists
    if not input_sheet in sheet_names:
        print(f"tetris.py error: Missing input_sheet '{input_sheet}' in file {input_spreadsheet}")
        print("- Skipping this row")
        continue

    svg_str = tree_paint(input_spreadsheet, input_sheet, levels, area, quality, borders)

    print("")

    got_valid_svg_file = len(svg_str) > 0
    if got_valid_svg_file :
        lib.save_as(output_svgfile, svg_str, verbose=True)