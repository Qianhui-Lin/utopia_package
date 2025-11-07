run-all:
	uvicorn src.utopia.microservice.load_user_data.load_user_data_app:app --reload --port 8001 &
	uvicorn src.utopia.microservice.generate_object.generate_object_app_new:app --reload --port 8002 &
	uvicorn src.utopia.microservice.generate_rate_constant.generate_rate_constant_app:app --reload --port 8003 &
	uvicorn src.utopia.microservice.plot_rate_constant.plot_rate_constant_app:app --reload --port 8004 &
	wait
