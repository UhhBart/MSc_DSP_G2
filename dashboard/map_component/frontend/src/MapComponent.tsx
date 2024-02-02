import {
  Streamlit,
  StreamlitComponentBase,
  withStreamlitConnection
} from "streamlit-component-lib";
import * as d3 from "d3";
import React, { ReactNode } from "react";
import { Slider, ConfigProvider, Button, Flex } from "antd";
import { UpSquareOutlined, DownSquareOutlined } from "@ant-design/icons";

interface State {
  fullGridIsDrawn: boolean;
  numRiskValues: number;
  currentRiskIndex: number;
}

// magic const which undos the mercator projection distortion
const MERCATOR_DISTORTION_RATIO = 0.6102207777653247;

/**
 * This is a React-based component template. The `render()` function is called
 * automatically when your component should be re-rendered.
 */
class MapComponent extends StreamlitComponentBase<State> {
  public state = {
    fullGridIsDrawn: false,
    numRiskValues: 1,
    currentRiskIndex: 0
  };

  private WIDTH = 700;
  private HEIGHT = 600;

  private UI_COLOUR = "#b00927";

  private risk2colour = (risk) => {
    return risk ? d3.interpolateYlOrRd(risk) : "#AAAAAA";
  };

  private resizeSVG = (svg) => {
    // get container + svg aspect ratio
    const container = d3.select(svg.node().parentNode);
    const width = this.WIDTH;
    const height = this.HEIGHT;
    const aspect = width / height;

    // get width of container and resize svg to fit it
    function resize() {
      const targetWidth = parseInt(container.style("width"));
      svg.style("width", targetWidth);
      svg.style("height", Math.round(targetWidth / aspect));
    }

    // add viewBox and preserveAspectRatio properties,
    // and call resize so that svg resizes on inital page load
    svg
      .attr("viewBox", "0 0 " + width + " " + height)
      .attr("perserveAspectRatio", "xMinYMid")
      .call(resize);

    d3.select(window).on("resize." + container.attr("id"), resize);
  };

  private PROJECTION = d3
    .geoPath()
    .projection(
      d3.geoMercator().center([4.88, 52.32]).scale(88000).translate([320, 290])
    );

  private SERVICE_AREA_ZOOMS: { [key: string]: d3.ZoomTransform } = {
    Aalsmeer: new d3.ZoomTransform(2.25, -50, -730),
    Amstelveen: new d3.ZoomTransform(2.25, -410, -510),
    Anton: new d3.ZoomTransform(2.25, -777, -340),
    Diemen: new d3.ZoomTransform(3.5, -1310, -570),
    Dirk: new d3.ZoomTransform(4.25, -1030, -630),
    Driemond: new d3.ZoomTransform(3.25, -1370, -740),
    Duivendrecht: new d3.ZoomTransform(4.25, -1360, -840),
    GBA: new d3.ZoomTransform(2.5, -180, 80),
    Hendrik: new d3.ZoomTransform(4.75, -1200, -400),
    IJsbrand: new d3.ZoomTransform(4, -1090, -10),
    Nico: new d3.ZoomTransform(4.75, -1500, -400),
    Osdorp: new d3.ZoomTransform(4, -460, -450),
    Pieter: new d3.ZoomTransform(4, -690, -610),
    Teunis: new d3.ZoomTransform(4, -840, -210),
    Uithoorn: new d3.ZoomTransform(3, -380, -1090),
    Victor: new d3.ZoomTransform(5, -1720, -650),
    Weesp: new d3.ZoomTransform(3.25, -1610, -815),
    Willem: new d3.ZoomTransform(4.25, -1240, -690),
    Zebra: new d3.ZoomTransform(2.25, -790, 40)
  };

  // Dark Map x, y
  // -560.3329292111933,
  // -453.47715175151257
  private BG_TRANSFORM = new d3.ZoomTransform(
    2.9526288113656984,
    -596.2462592893183,
    -442.9508150815907
  );

  private move_path2coords(
    path: string | null,
    coords: [number, number],
    size = 1
  ) {
    if (!path) {
      return;
    }

    // Extract coordinates using regular expression
    const coordinateRegex = /(-?\d+\.\d+|-?\d+),(-?\d+\.\d+|-?\d+)/g;
    const coordinates: number[][] = [];
    let match;

    while ((match = coordinateRegex.exec(path)) !== null) {
      const x = parseFloat(match[1]);
      const y = parseFloat(match[2]);
      coordinates.push([x, y]);
    }
    coordinates.push(coordinates[0]);

    // const adjustedCoordinates = coordinates.map(([x,y]) => [coords[0] + x*size/1000, coords[1] - (y*size/1000) * Math.cos((4.88 * Math.PI) / 180)]);
    const adjustedCoordinates = coordinates.map(([x, y]) => [
      coords[0] + (x * size) / 1000,
      coords[1] - ((y * size) / 1000) * MERCATOR_DISTORTION_RATIO
    ]);

    return [adjustedCoordinates];
  }

  private draw_service_areas(zoom) {
    const shape = this.props.args["service_areas"],
      risks = this.props.args["risks"]["service_areas"],
      svg: any = d3.select("#map_svg"),
      tooltip = d3.select("#tooltip");

    svg
      .append("g")
      .attr("id", "service_area_g")
      .selectAll("path")
      .data(shape.features)
      .join("path")
      .attr("class", "service_area_path")
      .attr("d", this.PROJECTION)
      .attr("fill", (d: any) =>
        this.risk2colour(risks[d.properties.name][this.state.currentRiskIndex])
      )
      .style("opacity", 0.65)
      .style("stroke", "#222222")
      .style("stroke-width", 1.5)
      .on("click", (event, d) => {
        if (event.ctrlKey || event.metaKey) {
          svg
            .transition()
            .duration(500)
            .call(zoom.transform, this.SERVICE_AREA_ZOOMS[d.properties.name]);
          svg.selectAll("#grid_filter_g").remove();
          this.draw_grid(
            zoom,
            (f) => f.properties.service_area === d.properties.name
          );
          d3.select("#selected_g").raise();
        } else {
          Streamlit.setComponentValue({
            id: d.properties.id,
            name: d.properties.name,
            type: "service_area"
          });
          d3.select("#selected_g").raise();
          d3.select("#selected_area")
            .datum(d)
            .attr("class", "selected_path")
            .attr("d", this.PROJECTION)
            .attr("fill", "none")
            .style("stroke", "#111111")
            .style("stroke-width", 2.5)
            .style("opacity", 1)
            .style("visibility", "visible")
            .attr("pointer-events", "none")
            .attr("transform", d3.zoomTransform(svg.node()).toString());
        }
      })
      .on("mouseover", () => {
        tooltip.style("opacity", 1);
      })
      .on("mousemove", (event, d) => {
        tooltip
          .html(
            `Verzorgings gebied: ${d.properties.name}<br/>
                Schade Risico: ${risks[d.properties.name][this.state.currentRiskIndex].toFixed(2)}`
          )
          .style("top", event.pageY - 10 + "px")
          .style("left", event.pageX + 10 + "px");
      })
      .on("mouseleave", () => {
        tooltip.style("opacity", 0);
      });

    return;
  }

  private draw_zipcodes(zoom) {
    const shape = this.props.args["zipcodes"],
      risks = this.props.args["risks"]["zipcodes"],
      svg: any = d3.select("#map_svg"),
      tooltip = d3.select("#tooltip");

    svg
      .append("g")
      .attr("id", "zipcode_g")
      .selectAll("path")
      .data(shape.features)
      .join("path")
      .attr("class", "zipcode_path")
      .attr("d", this.PROJECTION)
      .attr("fill", (d: any) =>
        this.risk2colour(risks[d.properties.pc4_code][this.state.currentRiskIndex])
      )
      .style("opacity", 0.65)
      .style("stroke", "#222222")
      .style("stroke-width", 1.5)
      .on("click", (event, d) => {
        if (event.ctrlKey || event.metaKey) {
          // svg
          //   .transition()
          //   .duration(500)
          //   .call(zoom.transform, this.SERVICE_AREA_ZOOMS[d.properties.name]);
          // svg.selectAll("#grid_filter_g").remove();
          // this.draw_grid(
          //   zoom,
          //   (f) => f.properties.service_area === d.properties.name
          // );
          // d3.select("#selected_g").raise();
        } else {
          Streamlit.setComponentValue({
            id: d.properties.pc4_code,
            name: d.properties.pc4_code,
            type: "zipcode"
          });
          d3.select("#selected_g").raise();
          d3.select("#selected_area")
            .datum(d)
            .attr("class", "selected_path")
            .attr("d", this.PROJECTION)
            .attr("fill", "none")
            .style("stroke", "#111111")
            .style("stroke-width", 2.5)
            .style("opacity", 1)
            .style("visibility", "visible")
            .attr("pointer-events", "none")
            .attr("transform", d3.zoomTransform(svg.node()).toString());
        }
      })
      .on("mouseover", () => {
        tooltip.style("opacity", 1);
      })
      .on("mousemove", (event, d) => {
        tooltip
          .html(
            `Postcode: ${d.properties.pc4_code}<br/>
                Schade Risico: ${risks[d.properties.pc4_code][this.state.currentRiskIndex].toFixed(2)}`
          )
          .style("top", event.pageY - 10 + "px")
          .style("left", event.pageX + 10 + "px");
      })
      .on("mouseleave", () => {
        tooltip.style("opacity", 0);
      });

    return;
  }

  private draw_grid(
    zoom,
    shape_filter?: (value: any) => boolean,
    opacity = 0.5
  ) {
    if (!shape_filter) {
      this.setState({ fullGridIsDrawn: true });
    }
    const shape = this.props.args["grid"],
      risks = this.props.args["risks"]["grid"],
      svg: any = d3.select("#map_svg"),
      tooltip = d3.select("#tooltip");

    svg
      .append("g")
      .attr("id", shape_filter ? "grid_filter_g" : "grid_g")
      .style(
        "visibility",
        shape_filter && this.state.fullGridIsDrawn ? "hidden" : "visible"
      )
      .selectAll("path")
      .data(shape_filter ? shape.features.filter(shape_filter) : shape.features)
      .join("path")
      .attr("class", "grid_path")
      .attr("fill", "none")
      .attr("d", this.PROJECTION)
      .style("fill", (d: any) =>
        this.risk2colour(risks[d.properties.id][this.state.currentRiskIndex])
      )
      .style("opacity", opacity)
      .on("click", (event, d) => {
        if (event.ctrlKey || event.metaKey) {
          svg
            .transition()
            .duration(500)
            .call(
              zoom.transform,
              this.SERVICE_AREA_ZOOMS[d.properties.service_area]
            );
          d3.select("#selected_g").raise();
        } else {
          Streamlit.setComponentValue({
            id: d.properties.id,
            name: d.properties.service_area,
            type: "grid"
          });
          d3.select("#selected_g").raise();
          d3.select("#selected_area")
            .raise()
            .datum(d)
            .attr("class", "selected_path")
            .attr("d", this.PROJECTION)
            .attr("fill", "none")
            .style("stroke", "#111111")
            .style("stroke-width", 1)
            .style("opacity", 1)
            .style("visibility", "visible")
            .attr("pointer-events", "none")
            .attr("transform", d3.zoomTransform(svg.node()).toString());
        }
      })
      .on("mouseover", () => {
        tooltip.style("opacity", 1);
      })
      .on("mousemove", (event, d) => {
        tooltip
          .html(
            `Verzorgings gebied: ${d.properties.service_area}<br/>
              Grid id: ${d.properties.id}<br/>
              Schade Risico: ${risks[d.properties.id][this.state.currentRiskIndex].toFixed(2)}`
          )
          .style("top", event.pageY - 10 + "px")
          .style("left", event.pageX + 10 + "px");
      })
      .on("mouseleave", () => {
        tooltip.style("opacity", 0);
      });

    return;
  }

  private draw_icons() {
    const shapes: Object = this.props.args["icons"],
      svg: any = d3.select("#map_svg");

    for (const [key, shape] of Object.entries(shapes)) {
      // TODO: Get icon using key
      // const icon = d3.symbolStar;
      const icon = d3.symbolStar;
      svg
        .append("g")
        .attr("class", `icon_g`)
        .attr("id", `icon_${key}_g`)
        .selectAll("path")
        .data(shape.features)
        .join("path")
        .attr("class", `icon_path`)
        .attr("d", (d) => {
          const polygon = {
            type: "Polygon",
            coordinates: this.move_path2coords(
              d3.symbol(icon)(),
              d.geometry.coordinates,
              0.5
            )
          };
          // @ts-ignore
          return this.PROJECTION(polygon);
        })
        .attr("pointer-events", "none")
        .attr("fill", "#6688FF")
        .style("stroke", "#111111")
        .style("stroke-width", 1);
    }

    return;
  }

  public componentDidMount(): void {
    console.log("mount");
    const map_bg = this.props.args["map_bg"];

    const width = this.WIDTH,
      height = this.HEIGHT;

    const svg: any = d3
      .select("#svg_div")
      .append("svg")
      .attr("id", "map_svg")
      .style("width", width)
      .style("height", height)
      .call(this.resizeSVG);

    svg
      .append("rect")
      .attr("id", "bg_rect")
      .style("width", "100%")
      .style("height", "100%")
      .style("opacity", 0)
      .on("click", (event) => {
        if (event.ctrlKey || event.metaKey) {
          svg.selectAll("#grid_filter_g").remove();
        } else {
          d3.select("#selected_area").style("visibility", "hidden");
        }
      });

    svg
      .append("g")
      .attr("id", "selected_g")
      .append("path")
      .attr("id", "selected_area");

    const BG_TRANSFORM = this.BG_TRANSFORM;

    function zoomFunc(e: any) {
      console.log(e.transform);
      d3.selectAll(".service_area_path, .zipcode_path, .grid_path, .selected_path, .icon_path").attr(
        "transform",
        e.transform
      );
      d3.selectAll("image").attr("transform", e.transform + BG_TRANSFORM);

      const newY = e.transform.rescaleY(y);
      const newX = e.transform.rescaleX(x);

      draw_axes(newX, newY, Y_GRIDS, X_GRIDS);
    }

    const zoom = d3
      .zoom()
      .scaleExtent([1, 15])
      .translateExtent([
        [-50, -50],
        [width + 50, height + 50]
      ])
      .on("zoom", zoomFunc);

    svg.call(zoom);

    // create a tooltip
    const tooltip = d3
      .select("#svg_div")
      .append("div")
      .attr("id", "tooltip")
      .attr("class", "tooltip")
      .style("opacity", 0)
      .style("background-color", "#FFFFFF")
      .style("border", "solid")
      .style("border-width", "2px")
      .style("border-radius", "5px")
      .style("padding", "5px")
      .style("pointer-events", "none");

    const bg_img = svg
      .append("image")
      .attr("xlink:href", `data:image/png;base64,${map_bg}`)
      .style("width", 600)
      .style("height", 500)
      .attr("transform", this.BG_TRANSFORM);

    this.draw_service_areas(zoom);
    this.draw_zipcodes(zoom);
    svg.selectAll("#zipcode_g").style("visibility", "hidden");

    this.draw_icons();

    const xAxis = svg
        .append("g")
        .attr("transform", `translate(0,${height})`)
        .attr("id", "myXaxis"),
      yAxis = svg.append("g").attr("id", "myYaxis");

    const Y_GRIDS = 12,
      X_GRIDS = 14,
      y = d3.scaleLinear().domain([0, Y_GRIDS]).range([height, 0]),
      x = d3.scaleLinear().domain([0, X_GRIDS]).range([0, width]);

    const draw_axes = (x: any, y: any, y_grids: number, x_grids: number) => {
      yAxis.call(
        d3
          .axisLeft(y)
          .tickSize(-width / y_grids / 2)
          .tickValues(Array.from({ length: y_grids }, (_, index) => index + 1))
          .tickFormat((d: any) => {
            if (d % 1 === 0) {
              return String(d);
            }
            return "";
          })
      );
      yAxis
        .selectAll("text")
        .style("font-size", "15")
        .attr("transform", `translate(20, ${height / y_grids / 4})`);

      xAxis.call(
        d3
          .axisBottom(x)
          .tickSize(-height / x_grids / 2)
          .tickValues(Array.from({ length: x_grids }, (_, index) => index + 1))
          .tickFormat((d: any) => {
            if (d % 1 === 0) {
              return `${String.fromCharCode(65 + d - 1)}`;
            }
            return "";
          })
      );
      xAxis
        .selectAll("text")
        .style("font-size", "15")
        .attr("transform", `translate(-${height / x_grids / 4}, -20)`);
    };
    draw_axes(x, y, Y_GRIDS, X_GRIDS);

    d3.select("#reset_button").on("click", () => {
      svg
        .transition()
        .duration(500)
        .call(zoom.transform, new d3.ZoomTransform(1, 0, 0));
    });

    // const risks = this.props.args["risks"]["service_areas"];

    d3.select("#service_area_button").on("click", () => {
      if (this.state.fullGridIsDrawn) {
        this.setState({ fullGridIsDrawn: false });
        svg.selectAll("#grid_g").remove();
        svg.selectAll("#grid_filter_g").style("visibility", "visible");
      } else {
        svg.selectAll("#grid_filter_g").remove();
      }
      svg.selectAll("#zipcode_g").style("visibility", "hidden");
      svg.selectAll("#service_area_g").style("visibility", "visible");

      d3.select("#selected_g").raise();
      d3.select(".icon_g").raise();
    });

    d3.select("#zipcode_button").on("click", () => {
      if (this.state.fullGridIsDrawn) {
        this.setState({ fullGridIsDrawn: false });
        svg.selectAll("#grid_g").remove();
        svg.selectAll("#grid_filter_g").style("visibility", "visible");
      } else {
        svg.selectAll("#grid_filter_g").remove();
      }
      svg.selectAll("#service_area_g").style("visibility", "hidden");
      svg.selectAll("#zipcode_g").style("visibility", "visible");

      d3.select("#selected_g").raise();
      d3.select(".icon_g").raise();
    });

    d3.select("#grid_button").on("click", () => {
      svg.selectAll("#grid_g").remove();
      svg.selectAll("#grid_filter_g").style("visibility", "hidden");
      this.draw_grid(zoom);
      const existingTransform = d3.zoomTransform(svg.node());
      d3.selectAll(".grid_path").attr(
        "transform",
        existingTransform.toString()
      );

      d3.select("#selected_g").raise();
      d3.select(".icon_g").raise();
    });

    Streamlit.setFrameHeight();
  }

  public componentDidUpdate(): void {
    console.log("update");
    const svg: any = d3.select("#map_svg").call(this.resizeSVG),
      risks_service_areas = this.props.args["risks"]["service_areas"],
      risks_zipcodes = this.props.args["risks"]["zipcodes"],
      risks_grid = this.props.args["risks"]["grid"];

    svg
      .selectAll(".service_area_path")
      .attr("fill", (d: any) =>
        this.risk2colour(
          risks_service_areas[d.properties.name][this.state.currentRiskIndex]
        )
      );
    svg
      .selectAll(".zipcode_path")
      .attr("fill", (d: any) =>
        this.risk2colour(
          risks_zipcodes[d.properties.pc4_code][this.state.currentRiskIndex]
        )
      );
    svg
      .selectAll(".grid_path")
      .style("fill", (d: any) =>
        this.risk2colour(
          risks_grid[d.properties.id][this.state.currentRiskIndex]
        )
      );

    Streamlit.setFrameHeight();
  }

  public render = (): ReactNode => {
    return (
      <span>
        <div id="svg_div" />
        <div
          id="contols_div"
          style={{
            textAlign: "right",
            paddingLeft: "1em",
            paddingRight: "1em"
          }}
        >
          <ConfigProvider
            theme={{
              components: {
                Slider: {
                  dotActiveBorderColor: this.UI_COLOUR,
                  dotBorderColor: this.UI_COLOUR,
                  handleActiveColor: this.UI_COLOUR,
                  handleColor: this.UI_COLOUR,
                  railBg: this.UI_COLOUR,
                  railHoverBg: this.UI_COLOUR,
                  trackBg: this.UI_COLOUR,
                  trackHoverBg: this.UI_COLOUR
                },
                Button: {
                  algorithm: true,
                  defaultBg: this.UI_COLOUR,
                  defaultBorderColor: this.UI_COLOUR,
                  groupBorderColor: this.UI_COLOUR,
                  dangerColor: "#FFFFFF",
                  dangerShadow: "#FFFFFF",
                  defaultColor: "#FFFFFF"
                }
              }
            }}
          >
            <Flex gap="small" vertical>
              <Flex justify="flex-start">
                Uren vooruit voorspeld:
              </Flex>
              <Slider
                id="time_slider"
                defaultValue={1}
                min={1}
                max={
                  this.props.args["risks"]["service_areas"][
                    Object.keys(this.props.args["risks"]["service_areas"])[0]
                  ].length
                }
                onChange={this.sliderOnChange}
                dots
                tipFormatter={(t) => `+${t} uur`}
              />
              <Flex gap="small" align="right" wrap="wrap" justify="flex-end">
                <Button id="reset_button">Reset Zoom</Button>
                <Button id="service_area_button"> Verzorgings Gebied </Button>
                <Button id="zipcode_button"> Postcodes </Button>
                <Button id="grid_button"> Grid </Button>
              </Flex>
            </Flex>
          </ConfigProvider>
        </div>
      </span>
    );
  };

  private sliderOnChange = (value: number) => {
    this.setState({ currentRiskIndex: value - 1});
  };
}
export default withStreamlitConnection(MapComponent);
