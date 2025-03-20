import gradio as gr

d3_html = """
<div id="chart" style="height: 300px; width: 100%; background-color: white;">
    <style>
        #chart {
            margin: 20px;
        }
    </style>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        // Wait for the DOM to load
        document.addEventListener('DOMContentLoaded', function() {
            // Data
            const data = [30, 86, 168, 281, 303];

            // Create SVG
            const svg = d3.select("#chart")
                .append("svg")
                .attr("width", "100%")
                .attr("height", "100%")
                .attr("viewBox", "0 0 400 200");

            // Create bars
            svg.selectAll("rect")
                .data(data)
                .enter()
                .append("rect")
                .attr("x", (d, i) => i * 70)
                .attr("y", d => 200 - d)
                .attr("width", 65)
                .attr("height", d => d)
                .attr("fill", "steelblue");
        });
    </script>
</div>"""

# Create Gradio interface
with gr.Blocks() as demo:
    with gr.Tab("D3 Chart"):
        gr.HTML(d3_html)
    with gr.Tab("Other"):
        gr.Textbox(label="Example")

demo.launch()
