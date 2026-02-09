#!/bin/bash

# Start all microservices in background
echo "Starting microservices..."

uvicorn src.utopia.microservice.load_user_data.load_user_data_app:app --reload --port 8001 &
uvicorn src.utopia.microservice.generate_object.generate_object_app_new:app --reload --port 8002 &
uvicorn src.utopia.microservice.generate_rate_constant.generate_rate_constant_app:app --reload --port 8003 &
uvicorn src.utopia.microservice.plot_rate_constant.plot_rate_constant_app:app --reload --port 8004 &
uvicorn src.utopia.microservice.generate_interaction_matrix.fill_interactions_df_app:app --reload --port 8005 &
uvicorn src.utopia.microservice.solve_steady_state.solver_steady_state_app:app --reload --port 8006 &
uvicorn src.utopia.microservice.estimate_flow.estimate_flow_app:app --reload --port 8007 &
uvicorn src.utopia.microservice.process_result.process_result_app:app --reload --port 8008 &
uvicorn src.utopia.microservice.plot_fraction_distribution.plot_fraction_distribution_app:app --reload --port 8009 &
uvicorn src.utopia.microservice.plot_compartment_distribution.plot_compartment_distribution_app:app --reload --port 8010 &
uvicorn src.utopia.microservice.calculate_exposure_indicator.calculate_exposure_indicator_app:app --reload --port 8011 &
uvicorn src.utopia.microservice.plot_emission_fraction.plot_emission_fraction_app:app --reload --port 8012 &

echo "All services started!"
echo "Press Ctrl+C to stop all services"

# Wait for user input to stop
wait