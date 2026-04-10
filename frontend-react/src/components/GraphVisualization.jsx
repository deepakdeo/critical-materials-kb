import { useState, useEffect, useRef, useCallback } from 'react'
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force'
import { select } from 'd3-selection'
import { drag as d3Drag } from 'd3-drag'
import { zoom as d3Zoom, zoomIdentity } from 'd3-zoom'

const NODE_STYLES = {
  Material:     { color: '#3b82f6', icon: '⬡', label: 'Material' },
  Company:      { color: '#10b981', icon: '●', label: 'Company' },
  Country:      { color: '#f59e0b', icon: '◆', label: 'Country' },
  WeaponSystem: { color: '#ef4444', icon: '▲', label: 'Weapon System' },
  Regulation:   { color: '#8b5cf6', icon: '■', label: 'Regulation' },
  DPAAward:     { color: '#ec4899', icon: '★', label: 'DPA Award' },
  Facility:     { color: '#06b6d4', icon: '⬢', label: 'Facility' },
}

function getStyle(type) {
  return NODE_STYLES[type] || NODE_STYLES.Material
}

function getNodeRadius(node, edges) {
  const connections = edges.filter(e => e.source === node.id || e.target === node.id
    || e.source?.id === node.id || e.target?.id === node.id).length
  return Math.max(22, Math.min(36, 18 + connections * 3))
}

export default function GraphVisualization({ graphData, dark }) {
  const [expanded, setExpanded] = useState(false)
  const [selectedNode, setSelectedNode] = useState(null)
  const svgRef = useRef(null)
  const simulationRef = useRef(null)
  const containerRef = useRef(null)

  const nodes = graphData?.nodes || []
  const edges = graphData?.edges || []
  const hasData = nodes.length > 0

  const width = 800
  const height = Math.max(450, Math.min(600, nodes.length * 30))

  // Build the D3 force simulation
  const buildGraph = useCallback(() => {
    if (!svgRef.current || !expanded || nodes.length === 0) return

    const svg = select(svgRef.current)
    svg.selectAll('*').remove()

    // Deep copy nodes/edges so D3 can mutate them
    const simNodes = nodes.map(n => ({ ...n }))
    const simEdges = edges.map(e => ({ ...e, source: e.source, target: e.target }))

    // Container group for zoom/pan
    const g = svg.append('g').attr('class', 'graph-container')

    // Zoom behavior
    const zoomBehavior = d3Zoom()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
      })
    svg.call(zoomBehavior)

    // Arrow marker
    const defs = g.append('defs')
    defs.append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 0 10 7')
      .attr('refX', 10)
      .attr('refY', 3.5)
      .attr('markerWidth', 8)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('polygon')
      .attr('points', '0 0, 10 3.5, 0 7')
      .attr('fill', dark ? '#64748b' : '#94a3b8')

    defs.append('marker')
      .attr('id', 'arrow-active')
      .attr('viewBox', '0 0 10 7')
      .attr('refX', 10)
      .attr('refY', 3.5)
      .attr('markerWidth', 8)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('polygon')
      .attr('points', '0 0, 10 3.5, 0 7')
      .attr('fill', dark ? '#60a5fa' : '#2563eb')

    // Drop shadow filter
    const filter = defs.append('filter').attr('id', 'drop-shadow')
      .attr('x', '-40%').attr('y', '-40%').attr('width', '180%').attr('height', '180%')
    filter.append('feDropShadow')
      .attr('dx', 0).attr('dy', 2).attr('stdDeviation', 3)
      .attr('flood-color', dark ? 'rgba(0,0,0,0.5)' : 'rgba(0,0,0,0.15)')

    // Glow filter
    const glow = defs.append('filter').attr('id', 'glow')
      .attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%')
    glow.append('feGaussianBlur').attr('stdDeviation', 4).attr('result', 'blur')
    const merge = glow.append('feMerge')
    merge.append('feMergeNode').attr('in', 'blur')
    merge.append('feMergeNode').attr('in', 'SourceGraphic')

    // Edge lines
    const edgeGroup = g.append('g').attr('class', 'edges')
    const link = edgeGroup.selectAll('line')
      .data(simEdges)
      .join('line')
      .attr('stroke', dark ? '#475569' : '#cbd5e1')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#arrow)')

    // Edge labels
    const edgeLabels = edgeGroup.selectAll('text')
      .data(simEdges)
      .join('text')
      .text(d => d.label)
      .attr('text-anchor', 'middle')
      .attr('font-size', 8)
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .attr('fill', dark ? '#64748b' : '#94a3b8')
      .attr('font-weight', 500)
      .style('pointer-events', 'none')

    // Node groups
    const nodeGroup = g.append('g').attr('class', 'nodes')
    const node = nodeGroup.selectAll('g')
      .data(simNodes)
      .join('g')
      .attr('class', 'node-group')
      .style('cursor', 'grab')

    // Node circles
    node.append('circle')
      .attr('r', d => getNodeRadius(d, edges))
      .attr('fill', d => getStyle(d.type).color)
      .attr('stroke', d => {
        const c = getStyle(d.type).color
        // Darker border
        return dark ? c : c
      })
      .attr('stroke-width', 2)
      .attr('filter', 'url(#drop-shadow)')
      .attr('opacity', 0.92)

    // Node labels (inside circle)
    node.append('text')
      .text(d => d.label.length > 14 ? d.label.slice(0, 12) + '…' : d.label)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('font-size', d => d.label.length > 12 ? 7.5 : 9)
      .attr('font-weight', 600)
      .attr('fill', '#ffffff')
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .style('pointer-events', 'none')

    // Type labels below
    node.append('text')
      .text(d => getStyle(d.type).label)
      .attr('text-anchor', 'middle')
      .attr('dy', d => getNodeRadius(d, edges) + 13)
      .attr('font-size', 7)
      .attr('font-weight', 500)
      .attr('fill', dark ? '#64748b' : '#94a3b8')
      .attr('font-family', 'Inter, system-ui, sans-serif')
      .style('pointer-events', 'none')

    // Tooltip on hover
    const tooltip = g.append('g').attr('class', 'tooltip').style('display', 'none')
    const tooltipRect = tooltip.append('rect')
      .attr('rx', 6).attr('ry', 6)
      .attr('fill', dark ? '#1e293b' : '#0f172a')
      .attr('opacity', 0.92)
    const tooltipText = tooltip.append('text')
      .attr('text-anchor', 'middle')
      .attr('fill', '#f8fafc')
      .attr('font-size', 10)
      .attr('font-weight', 500)
      .attr('font-family', 'Inter, system-ui, sans-serif')

    node
      .on('mouseenter', (event, d) => {
        const r = getNodeRadius(d, edges)
        tooltipText.text(d.label)
        const textBBox = tooltipText.node().getBBox()
        tooltipRect
          .attr('x', textBBox.x - 8)
          .attr('y', textBBox.y - 4)
          .attr('width', textBBox.width + 16)
          .attr('height', textBBox.height + 8)
        tooltip
          .attr('transform', `translate(${d.x}, ${d.y - r - 16})`)
          .style('display', 'block')

        // Highlight connected
        const connected = new Set([d.id])
        simEdges.forEach(e => {
          const sid = typeof e.source === 'object' ? e.source.id : e.source
          const tid = typeof e.target === 'object' ? e.target.id : e.target
          if (sid === d.id) connected.add(tid)
          if (tid === d.id) connected.add(sid)
        })

        node.select('circle')
          .attr('opacity', n => connected.has(n.id) ? 1 : 0.25)
          .attr('filter', n => n.id === d.id ? 'url(#glow)' : connected.has(n.id) ? 'url(#drop-shadow)' : 'none')
        node.selectAll('text')
          .attr('opacity', n => connected.has(n.id) ? 1 : 0.25)
        link
          .attr('opacity', e => {
            const sid = typeof e.source === 'object' ? e.source.id : e.source
            const tid = typeof e.target === 'object' ? e.target.id : e.target
            return sid === d.id || tid === d.id ? 1 : 0.1
          })
          .attr('stroke', e => {
            const sid = typeof e.source === 'object' ? e.source.id : e.source
            const tid = typeof e.target === 'object' ? e.target.id : e.target
            return (sid === d.id || tid === d.id) ? (dark ? '#60a5fa' : '#2563eb') : (dark ? '#475569' : '#cbd5e1')
          })
          .attr('stroke-width', e => {
            const sid = typeof e.source === 'object' ? e.source.id : e.source
            const tid = typeof e.target === 'object' ? e.target.id : e.target
            return (sid === d.id || tid === d.id) ? 2.5 : 1.5
          })
          .attr('marker-end', e => {
            const sid = typeof e.source === 'object' ? e.source.id : e.source
            const tid = typeof e.target === 'object' ? e.target.id : e.target
            return (sid === d.id || tid === d.id) ? 'url(#arrow-active)' : 'url(#arrow)'
          })
        edgeLabels
          .attr('opacity', e => {
            const sid = typeof e.source === 'object' ? e.source.id : e.source
            const tid = typeof e.target === 'object' ? e.target.id : e.target
            return sid === d.id || tid === d.id ? 1 : 0.1
          })
          .attr('fill', e => {
            const sid = typeof e.source === 'object' ? e.source.id : e.source
            const tid = typeof e.target === 'object' ? e.target.id : e.target
            return (sid === d.id || tid === d.id) ? (dark ? '#60a5fa' : '#2563eb') : (dark ? '#64748b' : '#94a3b8')
          })
          .attr('font-weight', e => {
            const sid = typeof e.source === 'object' ? e.source.id : e.source
            const tid = typeof e.target === 'object' ? e.target.id : e.target
            return (sid === d.id || tid === d.id) ? 600 : 500
          })
      })
      .on('mouseleave', () => {
        tooltip.style('display', 'none')
        node.select('circle').attr('opacity', 0.92).attr('filter', 'url(#drop-shadow)')
        node.selectAll('text').attr('opacity', 1)
        link
          .attr('opacity', 1)
          .attr('stroke', dark ? '#475569' : '#cbd5e1')
          .attr('stroke-width', 1.5)
          .attr('marker-end', 'url(#arrow)')
        edgeLabels
          .attr('opacity', 1)
          .attr('fill', dark ? '#64748b' : '#94a3b8')
          .attr('font-weight', 500)
      })
      .on('click', (event, d) => {
        event.stopPropagation()
        setSelectedNode(prev => prev?.id === d.id ? null : d)
      })

    // Drag behavior
    const dragBehavior = d3Drag()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
        select(event.sourceEvent.target.closest('.node-group')).style('cursor', 'grabbing')
      })
      .on('drag', (event, d) => {
        d.fx = event.x
        d.fy = event.y
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0)
        d.fx = null
        d.fy = null
        select(event.sourceEvent.target.closest('.node-group')).style('cursor', 'grab')
      })
    node.call(dragBehavior)

    // Force simulation
    const simulation = forceSimulation(simNodes)
      .force('link', forceLink(simEdges)
        .id(d => d.id)
        .distance(140)
        .strength(0.4)
      )
      .force('charge', forceManyBody()
        .strength(-500)
        .distanceMax(400)
      )
      .force('center', forceCenter(width / 2, height / 2))
      .force('collide', forceCollide()
        .radius(d => getNodeRadius(d, edges) + 15)
        .strength(0.8)
      )
      .on('tick', () => {
        link
          .attr('x1', d => d.source.x)
          .attr('y1', d => d.source.y)
          .attr('x2', d => {
            const dx = d.target.x - d.source.x
            const dy = d.target.y - d.source.y
            const dist = Math.sqrt(dx * dx + dy * dy)
            const r = getNodeRadius(d.target, edges)
            return d.target.x - (dx / Math.max(dist, 1)) * (r + 2)
          })
          .attr('y2', d => {
            const dx = d.target.x - d.source.x
            const dy = d.target.y - d.source.y
            const dist = Math.sqrt(dx * dx + dy * dy)
            const r = getNodeRadius(d.target, edges)
            return d.target.y - (dy / Math.max(dist, 1)) * (r + 2)
          })

        edgeLabels
          .attr('x', d => (d.source.x + d.target.x) / 2)
          .attr('y', d => (d.source.y + d.target.y) / 2 - 8)

        node.attr('transform', d => `translate(${d.x},${d.y})`)
      })

    simulationRef.current = simulation

    // Click on background to deselect
    svg.on('click', () => setSelectedNode(null))

    // Fit to view after simulation settles
    setTimeout(() => {
      svg.call(zoomBehavior.transform, zoomIdentity)
    }, 100)

    return () => {
      simulation.stop()
    }
  }, [expanded, nodes, edges, dark])

  useEffect(() => {
    const cleanup = buildGraph()
    return () => cleanup?.()
  }, [buildGraph])

  if (!hasData) return null

  const nodeTypes = [...new Set(nodes.map(n => n.type))]

  // Connected edges for detail panel
  const connectedEdges = selectedNode
    ? edges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id)
    : []

  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
        Knowledge Graph ({nodes.length} nodes, {edges.length} relationships)
        <svg className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div ref={containerRef} className="mt-2 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden bg-white dark:bg-slate-900">
          {/* Legend + controls */}
          <div className="px-3 sm:px-4 py-2 sm:py-2.5 border-b border-slate-100 dark:border-slate-800 flex flex-wrap items-center gap-2 sm:gap-4">
            {nodeTypes.map(type => (
              <div key={type} className="flex items-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs text-slate-600 dark:text-slate-400">
                <span
                  className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full ring-1 ring-black/10"
                  style={{ backgroundColor: getStyle(type).color }}
                />
                {getStyle(type).label}
              </div>
            ))}
            <span className="hidden sm:inline ml-auto text-[10px] text-slate-400 dark:text-slate-500">
              Drag nodes &middot; Scroll to zoom &middot; Click to select
            </span>
          </div>

          {/* Graph SVG */}
          <svg
            ref={svgRef}
            viewBox={`0 0 ${width} ${height}`}
            className="w-full bg-slate-50/50 dark:bg-slate-800/30"
            style={{ maxHeight: '550px', minHeight: '350px' }}
          />

          {/* Node detail panel */}
          {selectedNode && (() => {
            const style = getStyle(selectedNode.type)
            const related = connectedEdges.map(e => {
              const isSource = e.source === selectedNode.id
              const otherId = isSource ? e.target : e.source
              const otherNode = nodes.find(n => n.id === otherId)
              return { label: e.label, node: otherNode, direction: isSource ? 'out' : 'in' }
            }).filter(r => r.node)
            return (
              <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="w-3 h-3 rounded-full ring-1 ring-black/10"
                    style={{ backgroundColor: style.color }}
                  />
                  <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">{selectedNode.label}</span>
                  <span className="text-xs text-slate-400 dark:text-slate-500">{style.label}</span>
                </div>
                {related.length > 0 && (
                  <div className="space-y-1">
                    {related.map((r, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
                        <span className="text-slate-400">{r.direction === 'out' ? '→' : '←'}</span>
                        <span className="font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider" style={{ fontSize: '10px' }}>
                          {r.label}
                        </span>
                        <span className="text-slate-700 dark:text-slate-300 font-medium">{r.node.label}</span>
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: getStyle(r.node.type).color }}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })()}
        </div>
      )}
    </div>
  )
}
