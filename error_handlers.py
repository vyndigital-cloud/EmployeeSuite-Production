def register_errors(app):
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404
