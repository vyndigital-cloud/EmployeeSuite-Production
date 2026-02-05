def register_errors(app):
    """Register comprehensive error handlers"""
    from flask import jsonify
    from datetime import datetime
    from error_logging import error_logger
    
    @app.errorhandler(500)
    def internal_error(error):
        error_logger.log_error(error, "INTERNAL_SERVER_ERROR")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Error has been logged and will be investigated',
            'error_id': datetime.now().strftime('%Y%m%d_%H%M%S')
        }), 500
    
    @app.errorhandler(404)
    def not_found_error(error):
        error_logger.log_error(error, "NOT_FOUND")
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        error_logger.log_error(error, "FORBIDDEN")
        return jsonify({
            'error': 'Forbidden',
            'message': 'Access denied'
        }), 403
