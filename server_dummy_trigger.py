@app.route('/api/debug/reload', methods=['POST'])
def debug_reload():
    """Force reload helper"""
    print("Debug: Triggering reload via file modification")
    return jsonify({'success': True})
