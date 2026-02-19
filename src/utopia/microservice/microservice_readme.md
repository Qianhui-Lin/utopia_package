### Run the microservice in root :
uvicorn src.utopia.microservice.load_user_data.load_user_data_app:app --reload --port 8001

uvicorn src.utopia.microservice.generate_object.generate_object_app_new:app --reload --port 8002

uvicorn src.utopia.microservice.calculate_exposure_indicator.calculate_exposure_indicator_app:app --reload --port 8011

uvicorn src.utopia.microservice.plot_emission_fraction.plot_emission_fraction_app:app --reload --port 8012