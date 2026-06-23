def build_timeline_html(sources):
    """
    Builds HTML for the timeline based on sources retrieved.
    `sources` is a list of dicts: {"title": ..., "timestamp": "MM:SS", "seconds": float}
    """
    if not sources:
        return "<p style='color:#666;'>Ask a question to generate a smart timeline.</p>"
        
    html = "<div class='timeline-container' style='padding:15px; border:1px solid #e5e7eb; border-radius:8px; background:#fafafa;'>"
    html += "<h3 style='margin-top:0;'>Smart Timeline Navigation</h3><ul style='list-style-type:none; padding-left:0; margin-bottom:0;'>"
    
    # Sort chronologically and deduplicate overlapping timestamps
    unique_sources = {}
    for s in sources:
        # Group by 10-second windows to merge overlapping chunks
        window = int(s.get('seconds', 0) // 10) * 10
        if window not in unique_sources:
            unique_sources[window] = s
            
    sorted_sources = sorted(unique_sources.values(), key=lambda x: x.get('seconds', 0))
    
    for s in sorted_sources:
        time_str = s.get('timestamp', '00:00')
        title = s.get('title', 'Segment')
        seconds = s.get('seconds', 0)
        
        html += f"""
        <li style='margin-bottom:10px; display:flex; align-items:center;'>
            <button onclick='seekVideo({seconds})' style='background:#2563eb; color:white; border:none; border-radius:4px; padding:6px 12px; cursor:pointer; font-weight:600; font-size:0.9rem;'>
                ▶ {time_str}
            </button>
            <span style='margin-left:12px; font-weight:500; color:#374151;'>{title}</span>
        </li>
        """
    html += "</ul></div>"
    
    # Javascript to seek the first video player found in the DOM
    html += """
    <script>
    function seekVideo(seconds) {
        var videos = document.querySelectorAll('video');
        if(videos.length > 0) {
            videos[0].currentTime = seconds;
            videos[0].play();
        }
    }
    </script>
    """
    return html
