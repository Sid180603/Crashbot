/**
 * PHASE 3.5: Stack Trace Visualization
 * Interactive stack trace viewer with D3.js
 */
'use client';

import React, { useEffect, useRef } from 'react';
import { Box, Paper, Typography } from '@mui/material';
import * as d3 from 'd3';

interface StackFrame {
  index: number;
  module?: string;
  function?: string;
  address?: string;
  offset?: string;
}

interface StackTraceVisualizationProps {
  stackFrames: StackFrame[];
  faultingModule?: string;
}

export const StackTraceVisualization: React.FC<StackTraceVisualizationProps> = ({
  stackFrames,
  faultingModule,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !stackFrames.length) return;

    // Clear previous visualization
    d3.select(svgRef.current).selectAll('*').remove();

    // Setup dimensions
    const width = svgRef.current.clientWidth;
    const height = stackFrames.length * 40;
    const margin = { top: 20, right: 20, bottom: 20, left: 200 };

    const svg = d3
      .select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    // Create groups for each frame
    const frameGroups = svg
      .selectAll('g')
      .data(stackFrames)
      .enter()
      .append('g')
      .attr('transform', (d, i) => `translate(0, ${i * 40 + margin.top})`);

    // Add rectangles
    frameGroups
      .append('rect')
      .attr('x', margin.left)
      .attr('y', 0)
      .attr('width', width - margin.left - margin.right)
      .attr('height', 35)
      .attr('fill', (d) =>
        d.module === faultingModule ? '#ff6b6b' : '#4dabf7'
      )
      .attr('opacity', 0.7)
      .attr('rx', 5);

    // Add function names
    frameGroups
      .append('text')
      .attr('x', margin.left + 10)
      .attr('y', 22)
      .text((d) => `${d.module || 'Unknown'}!${d.function || 'Unknown'}`)
      .attr('fill', 'white')
      .attr('font-size', '12px')
      .attr('font-family', 'monospace');

    // Add frame indices
    frameGroups
      .append('text')
      .attr('x', margin.left - 10)
      .attr('y', 22)
      .text((d) => `#${d.index}`)
      .attr('text-anchor', 'end')
      .attr('fill', '#666')
      .attr('font-size', '12px');

  }, [stackFrames, faultingModule]);

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Typography variant="h6" gutterBottom>
        Stack Trace Visualization
      </Typography>
      <Box sx={{ overflowX: 'auto' }}>
        <svg ref={svgRef} style={{ width: '100%' }} />
      </Box>
    </Paper>
  );
};
