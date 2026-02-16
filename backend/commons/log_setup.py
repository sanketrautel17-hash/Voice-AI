import logging


def setup_loguru():
    """
    Redirects loguru logs to the standard logging module.
    This ensures that logs from libraries using loguru (like pipecat)
    appear in our debug.log file.
    """
    try:
        from loguru import logger

        class LoguruSink:
            def write(self, message):
                record = message.record
                level_name = record["level"].name

                # Map loguru levels to logging levels
                level_map = {
                    "TRACE": logging.DEBUG,
                    "DEBUG": logging.DEBUG,
                    "INFO": logging.INFO,
                    "SUCCESS": logging.INFO,
                    "WARNING": logging.WARNING,
                    "ERROR": logging.ERROR,
                    "CRITICAL": logging.CRITICAL,
                }

                level = level_map.get(level_name, logging.INFO)

                # Dispatch to standard logging
                # We use the record's name to preserve the module source
                logging.getLogger(record["name"]).log(level, record["message"])

        # Remove default handlers to avoid double logging (console)
        logger.remove()

        # Add our custom sink
        # We don't need to format the message here as standard logging will format it
        logger.add(LoguruSink(), format="{message}")

    except ImportError:
        # Loguru not installed, nothing to do
        pass
