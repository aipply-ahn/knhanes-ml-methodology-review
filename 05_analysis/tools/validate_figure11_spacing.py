#!/usr/bin/env python3
"""Rebuild both Figure 11 versions and check final rendered label geometry."""
import itertools
import tempfile
import make_pipeline_figures as pipeline
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np
import make_streamlined_figures as figures


def main():
    temporary = tempfile.TemporaryDirectory(prefix="figure11_geometry_")
    figures.OUT = pipeline.OUT = temporary.name
    original_save = figures.save
    results = []

    def checked_save(fig, name):
        original_save(fig, name)
        FigureCanvasAgg(fig)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        a, b, c, d = fig.axes
        checks = {}
        for letter, axis in zip("ABCD", fig.axes):
            boxes = [t.get_window_extent(renderer) for t in axis.get_yticklabels()]
            checks[f"{letter}_adjacent_y_labels_separated"] = all(
                not x.overlaps(y) for x, y in itertools.combinations(boxes, 2))
            checks[f"{letter}_multiline_spacing"] = all(
                (.80 <= t._linespacing <= .90 if letter == 'A' else t._linespacing >= 1.1)
                for t in axis.get_yticklabels())
        centers = a.transData.transform([(0, i) for i in range(8)])[:, 1]
        boxes_a = [t.get_window_extent(renderer) for t in a.get_yticklabels()]
        checks['A_eight_labels_centered_on_bars'] = len(boxes_a) == 8 and all(
            abs((box.y0 + box.y1)/2 - center) < 1 for box, center in zip(boxes_a, centers))
        checks['A_uniform_row_centers'] = bool(np.allclose(np.diff(centers), np.diff(centers)[0]))
        # Inter-label whitespace must exceed within-label baseline spacing.
        gaps = [boxes_a[i].y0 - boxes_a[i+1].y1 for i in range(7)]
        leading = max(t.get_fontsize()*fig.dpi/72*t._linespacing for t in a.get_yticklabels())
        checks['A_interlabel_gap_exceeds_leading'] = bool(min(gaps) > leading)
        checks["BC_four_row_centres_aligned"] = bool(np.allclose(
            b.transData.transform([(0, i) for i in range(4)])[:, 1],
            c.transData.transform([(0, i) for i in range(4)])[:, 1]))
        checks["BC_equal_plot_height"] = bool(np.isclose(
            b.get_position().height, c.get_position().height))
        checks["A_percent_axis_title_clear_of_legend"] = not a.xaxis.label.get_text() or not (
            a.xaxis.label.get_window_extent(renderer).overlaps(
                a.get_legend().get_window_extent(renderer)))
        checks["legends_clear_of_panel_titles"] = all(
            not axis.get_legend().get_window_extent(renderer).overlaps(
                title.get_window_extent(renderer))
            for axis in (a, b, c) for title in fig.texts)
        checks["B_axis_title_clear_of_legend"] = not b.xaxis.label.get_text() or not (
            b.xaxis.label.get_window_extent(renderer).overlaps(
                b.get_legend().get_window_extent(renderer)))
        boxes = [t.get_window_extent(renderer) for t in a.texts]
        checks["A_count_percent_labels_separated"] = all(
            not x.overlaps(y) for x, y in itertools.combinations(boxes, 2))
        from matplotlib.collections import LineCollection, PathCollection
        from matplotlib.transforms import Bbox
        ratio_boxes = [t.get_window_extent(renderer) for t in c.texts]
        distances = []
        for text_box in ratio_boxes:
            for collection in c.collections:
                if isinstance(collection, LineCollection):
                    for segment in collection.get_segments():
                        pts = c.transData.transform(segment)
                        radius = float(max(collection.get_linewidths()))*fig.dpi/72/2
                        obstacle = Bbox.from_extents(min(pts[:,0])-radius,min(pts[:,1])-radius,
                                                   max(pts[:,0])+radius,max(pts[:,1])+radius)
                        dx=max(obstacle.x0-text_box.x1,text_box.x0-obstacle.x1,0)
                        dy=max(obstacle.y0-text_box.y1,text_box.y0-obstacle.y1,0)
                        distances.append(float(np.hypot(dx,dy)))
                elif isinstance(collection, PathCollection):
                    radius=(float(np.sqrt(max(collection.get_sizes())))/2+float(max(collection.get_linewidths()))/2)*fig.dpi/72
                    for x,y in c.transData.transform(collection.get_offsets()):
                        dx=max(text_box.x0-x,x-text_box.x1,0);dy=max(text_box.y0-y,y-text_box.y1,0)
                        distances.append(float(np.hypot(dx,dy)-radius))
        checks['D_major_count_labels_inside_bars'] = all(
            any(patch.get_window_extent(renderer).contains(box.x0,box.y0) and
                patch.get_window_extent(renderer).contains(box.x1,box.y1) for patch in d.patches)
            for box in [t.get_window_extent(renderer) for t in d.texts if '/' in t.get_text()])
        checks['C_all_four_ratios_clear_of_all_marks'] = len(ratio_boxes)==4 and min(distances)>=2
        checks['C_ratios_clear_of_adjacent_labels_and_titles'] = all(
            not box.overlaps(other) for box in ratio_boxes for other in
            [t.get_window_extent(renderer) for t in c.get_yticklabels()]+[t.get_window_extent(renderer) for t in fig.texts])
        checks['panel_titles_mutually_separated'] = all(not x.overlaps(y) for x,y in itertools.combinations([t.get_window_extent(renderer) for t in fig.texts],2))
        checks['C_ratios_mutually_separated'] = all(not x.overlaps(y) for x,y in itertools.combinations(ratio_boxes,2))
        results.append({"figure": name, "checks": checks, 'C_min_ratio_mark_clearance_px':min(distances),
                        'A_min_interlabel_gap_px':float(min(gaps)), 'A_within_label_leading_px':float(leading)})
        assert all(checks.values()), results[-1]

    figures.save = checked_save
    for lang in ("en", "ko"):
        figures.figure10_reproducibility(lang)
    output = Path(figures.PROJ) / "prompts/implementation_records/openalex_source_dedup/figure11_spacing.json"
    output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    temporary.cleanup()


if __name__ == "__main__":
    main()
