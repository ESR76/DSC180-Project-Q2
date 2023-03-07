from sklearn import tree
import pandas as pd
import numpy as np
import os

def reduce_setpoint(x, val, min_val = 0):
	reduced = x - val
	return max(reduced, min_val)

def low_barrier(x, val, min_val = 0):
	reduced = x - val
	if reduced < min_val:
		return True
	return False

def optimize_model(cwd, model, is_train, **params):
	final_name = params['optimize_results']
	output_col = params['output_col']
	data = pd.DataFrame()
	direc = ""

	if is_train:
		direc = params['final_output']
	else:
		print("\nin run -> optimize for test data")
		direc = params['test_directory']

	if os.path.isdir(cwd + params['optimize_versions_folder']):
			files = os.listdir(cwd + direc)

			if final_name in files:
				print('Optimize data already found - will skip regenerating to save time.')
				print('To regenerate - please run "python3 run.py clean" before calling optimize again.')

				return pd.read_csv(cwd + direc + final_name)
	else:
		os.mkdir(cwd + params['optimize_versions_folder'])

	data = pd.read_csv(cwd + direc + params['train_data'])

	Xtrain = data.drop([output_col], axis = 1)
	Ytrain = data.loc[:, output_col]

	clf = model
	clf = clf.fit(Xtrain, Ytrain)

	opt_options = params["optimize_options"]
	columns = list(opt_options.keys())

	dfs = []
	results = []

	# OPTIMIZE TO DO - some kind of analysis of prop boundary via hours

	Xtest = Xtrain.copy(deep = True)

	# Makes 3 versions, one for high occupancy minimum, one for low occupancy min, one for no occupancy (0)
	for a in opt_options[columns[1]]:
		for t in opt_options[columns[0]]:
			# occupied - low limit
			Xtest.loc[:, columns[0]] = Xtrain.loc[:, columns[0]].apply(reduce_setpoint, args = (t, ))
			Xtest.loc[:, columns[1]] = Xtrain.loc[:, columns[1]].apply(reduce_setpoint, args = (a, params['optimization_room_min'], ))
			
			prop_limited = sum(Xtrain.loc[:, columns[1]].apply(low_barrier, args = (a, params['optimization_room_min'], ))) / Xtrain.shape[0]

			y_pred = clf.predict(Xtest)
			pred_series = pd.Series(y_pred).rename("preds")
			differences = Ytrain - pred_series

			dfs.append(Xtest)
			results.append((t, a, "occupied_low", prop_limited, differences.mean(), differences.median(), differences.min(), differences.max()))


			# occupied - high limit
			Xtest.loc[:, columns[1]] = Xtrain.loc[:, columns[1]].apply(reduce_setpoint, args = (a, params['optimization_room_avgmin'], ))
			prop_limited = sum(Xtrain.loc[:, columns[1]].apply(low_barrier, args = (a, params['optimization_room_avgmin'], ))) / Xtrain.shape[0]
			y_pred = clf.predict(Xtest)
			pred_series = pd.Series(y_pred).rename("preds")
			differences = Ytrain - pred_series

			dfs.append(Xtest)
			results.append((t, a, "occupied_high", prop_limited, differences.mean(), differences.median(), differences.min(), differences.max()))


			# unoccupied
			Xtest.loc[:, columns[1]] = Xtrain.loc[:, columns[1]].apply(reduce_setpoint, args = (a, ))
			prop_limited = sum(Xtrain.loc[:, columns[1]].apply(low_barrier, args = (a, ))) / Xtrain.shape[0]
			
			y_pred = clf.predict(Xtest)
			pred_series = pd.Series(y_pred).rename("preds")
			differences = Ytrain - pred_series

			dfs.append(Xtest)
			results.append((t, a, "unoccupied", prop_limited, differences.mean(), differences.median(), differences.min(), differences.max()))

	# WOULD IT BE POSSIBLE TO USE .DESCRIBE instead of PULLING OUT MAX/VARIABLES?

	pred_df = pd.DataFrame(results, columns = ['temp_decrease', 'air_decrease', 'air_limited', 'prop_boundary', 'mean_difference', 'median_difference', 'min_difference', 'max_difference'])

	for i, df in enumerate(dfs):
		df.to_csv(cwd + params['optimize_versions_folder'] + 'optimize_t{0}_a{1}_{2}.csv'.format(str(pred_df.loc[i, 'temp_decrease']).replace(".", ""), pred_df.loc[i, 'air_decrease'], pred_df.loc[i, 'air_limited']), index = False)

	if is_train:
		pred_df.to_csv(cwd + params['final_output'] + final_name, index = False)
	else:
		pred_df.to_csv(cwd + params['test_directory'] + final_name, index = False)
	
	return pred_df