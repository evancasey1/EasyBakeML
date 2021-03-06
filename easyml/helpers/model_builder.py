import json

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.neighbors.nearest_centroid import NearestCentroid
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.naive_bayes import GaussianNB
from sklearn import svm

from .constants import COLUMN_TYPE, ALGORITHM, ALGORITHM_NAME_MAP, ALGORITHM_TYPES
from mainsite.models import CsvFile, CsvFileData, MLModel
from .util import get_dataframe
from .util import get_match_acc


def create_model(algorithm_type_num, file_id, parameters):
    file_data = CsvFileData.objects.filter(parent_file_id=file_id)\
        .exclude(type=COLUMN_TYPE.IGNORE).order_by('column_num')

    if file_data.count() == 0:
        print("Error: No data for file {}".format(file_id))
        return

    input_data = file_data.filter(type=COLUMN_TYPE.INPUT).order_by('column_num')
    target_data = file_data.filter(type=COLUMN_TYPE.TARGET)

    alg_type = ALGORITHM_NAME_MAP[algorithm_type_num]

    input_df = get_dataframe(input_data)
    target_df = get_dataframe(target_data)

    target_df = target_df.values.ravel()

    algorithm_type_nums = [algorithm_type_num]
    if algorithm_type_num == ALGORITHM.AUTOMATIC:
        alg_method = parameters['auto_alg_type']
        if alg_method == 'auto_classification':
            algorithm_type_nums = ALGORITHM_TYPES.CLASSIFICATION
        else:
            algorithm_type_nums = ALGORITHM_TYPES.REGRESSION

    best_acc = None
    best_acc_type = None
    best_model = None
    temp_model = None
    best_alg_type = alg_type
    for alg_type_num in algorithm_type_nums:
        if alg_type_num == ALGORITHM.LINEAR_REGRESSION:
            temp_model = create_linear_regression_model(input_df, target_df, parameters)

        elif alg_type_num == ALGORITHM.K_NEAREST_NEIGHBORS_CLASSIFIER:
            temp_model = create_k_nearest_neighbors_classifier(input_df, target_df, parameters)

        elif alg_type_num == ALGORITHM.K_NEAREST_NEIGHBORS_REGRESSOR:
            temp_model = create_k_nearest_neighbors_regressor(input_df, target_df, parameters)

        elif alg_type_num == ALGORITHM.LOGISTIC_REGRESSION:
            temp_model = create_logistic_regression_model(input_df, target_df, parameters)

        elif alg_type_num == ALGORITHM.NEAREST_CENTROID:
            temp_model = create_nearest_centroid(input_df, target_df, parameters)

        elif alg_type_num == ALGORITHM.LINEAR_DISCRIMINANT_ANALYSIS:
            temp_model = create_linear_discriminant_analysis(input_df, target_df, parameters)

        elif alg_type_num == ALGORITHM.DECISION_TREE_REGRESSOR:
            temp_model = create_decision_tree_regressor(input_df, target_df, parameters)

        elif alg_type_num == ALGORITHM.GAUSSIAN_NAIVE_BAYES:
            temp_model = create_gaussian_naive_bayes(input_df, target_df, parameters)

        elif alg_type_num == ALGORITHM.RANDOM_FOREST_CLASSIFIER:
            temp_model = create_random_forest_classifier(input_df, target_df, parameters)

        elif alg_type_num == ALGORITHM.RANDOM_FOREST_REGRESSOR:
            temp_model = create_random_forest_regressor(input_df, target_df, parameters)

        elif alg_type_num == ALGORITHM.SUPPORT_VECTOR_MACHINE_CLASSIFIER:
            temp_model = create_support_vector_machine_classifier(input_df, target_df, parameters)

        elif alg_type_num == ALGORITHM.SUPPORT_VECTOR_MACHINE_REGRESSOR:
            temp_model = create_support_vector_machine_regressor(input_df, target_df, parameters)

        if not best_acc or parameters['accuracy'] > best_acc:
            best_acc = parameters['accuracy']
            best_acc_type = parameters['accuracy_type']
            best_model = temp_model
            if algorithm_type_num == ALGORITHM.AUTOMATIC:
                best_alg_type = 'Automatic_' + ALGORITHM_NAME_MAP[alg_type_num]
            else:
                best_alg_type = ALGORITHM_NAME_MAP[alg_type_num]

    if best_model:
        save_model(best_model, best_alg_type, algorithm_type_num, file_id, parameters, best_acc, best_acc_type)


def save_model(model, alg_type, algorithm_type_num, file_id, parameters, best_acc, best_acc_type):
    parent_file = CsvFile.objects.get(id=file_id)
    display_name = "{}_{}".format(parent_file.display_name, alg_type)

    same_name_count = MLModel.objects.filter(name=parent_file.display_name, type=alg_type).count()
    if same_name_count > 0:
        display_name += ' ({})'.format(same_name_count)

    display_name = display_name.replace(' ', '_')

    model_obj = MLModel()
    model_obj.type = alg_type
    model_obj.type_num = algorithm_type_num
    model_obj.data = model
    model_obj.name = parent_file.display_name
    model_obj.display_name = display_name
    model_obj.parameters = json.dumps(parameters)
    model_obj.parent_file = CsvFile.objects.get(id=file_id)
    model_obj.accuracy = best_acc
    model_obj.accuracy_type = best_acc_type
    model_obj.save()


def create_linear_regression_model(input_df, target_df, parameters):
    fit_intercept = bool(parameters.get('linreg_fit_intercept', False))
    normalize = bool(parameters.get('linreg_normalize', False))

    x_train, x_test, y_train, y_test = train_test_split(input_df, target_df)
    lin_reg = LinearRegression(fit_intercept=fit_intercept, normalize=normalize)

    lin_reg_test = lin_reg.fit(x_train, y_train)
    score = round(lin_reg_test.score(x_test, y_test), 4)
    parameters['accuracy'] = score
    parameters['accuracy_type'] = 'R^2'
    lin_reg = lin_reg.fit(input_df, target_df)

    return lin_reg


def create_logistic_regression_model(input_df, target_df, parameters):
    logreg_penalty = parameters.get('logreg_penalty', 'l2')
    logreg_c_select = parameters.get('logreg_C_select', 'custom')
    logreg_fit_intercept = bool(parameters.get('logreg_fit_intercept', False))

    if logreg_penalty == 'l1':
        solver = 'liblinear'
    else:
        solver = 'lbfgs'

    if logreg_c_select == 'custom':
        logreg_c = int(parameters.get('logreg_C', 1.0))
        logreg = LogisticRegression(C=logreg_c,
                                    penalty=logreg_penalty,
                                    fit_intercept=logreg_fit_intercept,
                                    solver=solver)

    else:
        steps = [('std_scaler', StandardScaler())]
        steps += [('log_regression', LogisticRegression(penalty=logreg_penalty,
                                                        multi_class='auto',
                                                        fit_intercept=logreg_fit_intercept,
                                                        solver=solver))]
        pipe = Pipeline(steps)

        param_grid = {'log_regression__C': [0.0001, 0.001, 0.01, 0.1, 1, 10, 100, 1000]}
        logreg = GridSearchCV(estimator=pipe, param_grid=param_grid, cv=5)

    x_train, x_test, y_train, y_test = train_test_split(input_df, target_df)
    clf_test = logreg.fit(x_train, y_train)
    acc = get_match_acc(clf_test.predict(x_test), y_test)
    parameters['accuracy'] = acc
    parameters['accuracy_type'] = 'Accuracy [%]'

    clf = logreg.fit(input_df, target_df)
    return clf


def create_linear_discriminant_analysis(input_df, target_df, parameters):
    solver = parameters.get('lda_solver', 'svd')
    clf = LinearDiscriminantAnalysis(solver=solver)

    x_train, x_test, y_train, y_test = train_test_split(input_df, target_df)
    clf_test = clf.fit(x_train, y_train)
    acc = get_match_acc(clf_test.predict(x_test), y_test)
    parameters['accuracy'] = acc
    parameters['accuracy_type'] = 'Accuracy [%]'

    clf.fit(input_df, target_df)

    return clf


def create_decision_tree_regressor(input_df, target_df, parameters):
    criterion = parameters.get('dtr_criterion', 'mse')
    presort = bool(parameters.get('dtr_presort', False))
    max_depth_choice = parameters.get('dtr_max_depth', 'none')
    x_train, x_test, y_train, y_test = train_test_split(input_df, target_df)

    if max_depth_choice == 'none':
        best_depth = None

    elif max_depth_choice == 'custom':
        best_depth = parameters.get('dtr_custom_depth', None)

    else:
        r2_lst = []
        depth_iter = 5
        depth_start = 10

        depth_lst = []
        for i in range(depth_iter):
            depth_lst.append(depth_start**i)

        # Select model with best r^2 and least depth
        for depth in depth_lst:
            dt_regr = DecisionTreeRegressor(max_depth=depth, presort=presort, criterion=criterion)
            dt_regr.fit(x_train, y_train)
            r2_lst.append(dt_regr.score(x_test, y_test))

        depth_index, r2 = min(enumerate(r2_lst), key=lambda x: abs(x[1] - 1))
        best_depth = depth_lst[depth_index]

    dt_regr = DecisionTreeRegressor(max_depth=best_depth,
                                    presort=presort,
                                    criterion=criterion)

    regr_test = dt_regr.fit(x_train, y_train)
    score = round(regr_test.score(x_test, y_test), 4)
    parameters['accuracy'] = score
    parameters['accuracy_type'] = 'R^2'

    dt_regr.fit(input_df, target_df)

    return dt_regr


def create_gaussian_naive_bayes(input_df, target_df, parameters):
    gnb = GaussianNB()

    x_train, x_test, y_train, y_test = train_test_split(input_df, target_df)
    clf_test = gnb.fit(x_train, y_train)
    acc = get_match_acc(clf_test.predict(x_test), y_test)
    parameters['accuracy'] = acc
    parameters['accuracy_type'] = 'Accuracy [%]'

    gnb.fit(input_df, target_df)
    return gnb


def create_random_forest_classifier(input_df, target_df, parameters):
    criterion = parameters.get('rfc_criterion', 'gini')
    n_estimators = int(parameters.get('rfc_n_estimators', 100))
    depth_select = parameters.get('rfc_max_depth', 'none')
    x_train, x_test, y_train, y_test = train_test_split(input_df, target_df)

    if depth_select == 'none':
        best_depth = None

    elif depth_select == 'custom':
        best_depth = parameters.get('rfc_custom_depth', None)

    else:
        r2_lst = []
        depth_iter = 5
        depth_start = 10

        depth_lst = []
        for i in range(depth_iter):
            depth_lst.append(depth_start**i)

        # Select model with best r^2 and least depth
        for depth in depth_lst:
            rf_clf = RandomForestClassifier(n_estimators=n_estimators,
                                            max_depth=depth,
                                            criterion=criterion,
                                            oob_score=True)
            rf_clf.fit(x_train, y_train)
            r2_lst.append(rf_clf.oob_score_)

        depth_index, r2 = min(enumerate(r2_lst), key=lambda x: abs(x[1] - 1))
        best_depth = depth_lst[depth_index]

    rf_clf = RandomForestClassifier(n_estimators=n_estimators,
                                    max_depth=best_depth,
                                    criterion=criterion)

    clf_test = rf_clf.fit(x_train, y_train)
    acc = get_match_acc(clf_test.predict(x_test), y_test)
    parameters['accuracy'] = acc
    parameters['accuracy_type'] = 'Accuracy [%]'

    rf_clf.fit(input_df, target_df)
    return rf_clf


def create_random_forest_regressor(input_df, target_df, parameters):
    criterion = parameters.get('rfc_criterion', 'mse')
    n_estimators = int(parameters.get('rfc_n_estimators', 100))
    depth_select = parameters.get('rfc_max_depth', 'none')
    x_train, x_test, y_train, y_test = train_test_split(input_df, target_df)

    if depth_select == 'none':
        best_depth = None

    elif depth_select == 'custom':
        best_depth = parameters.get('rfc_custom_depth', None)

    else:
        r2_lst = []
        depth_iter = 5
        depth_start = 10

        depth_lst = []
        for i in range(depth_iter):
            depth_lst.append(depth_start**i)

        # Select model with best r^2 and least depth
        for depth in depth_lst:
            rf_regr_test = RandomForestRegressor(n_estimators=n_estimators,
                                                 max_depth=depth,
                                                 criterion=criterion,
                                                 oob_score=True)
            rf_regr_test.fit(x_train, y_train)
            r2_lst.append(rf_regr_test.oob_score_)

        depth_index, r2 = min(enumerate(r2_lst), key=lambda x: abs(x[1] - 1))
        best_depth = depth_lst[depth_index]

    rf_regr = RandomForestRegressor(n_estimators=n_estimators,
                                    max_depth=best_depth,
                                    criterion=criterion)

    regr_test = rf_regr.fit(x_train, y_train)
    score = round(regr_test.score(x_test, y_test), 4)
    parameters['accuracy'] = score
    parameters['accuracy_type'] = 'R^2'

    rf_regr.fit(input_df, target_df)

    return rf_regr


def create_k_nearest_neighbors_classifier(input_df, target_df, parameters):
    n_neighbors = int(parameters.get('nnc_k', 5))
    weights = parameters.get('weights', 'uniform')
    algorithm = parameters.get('algorithm', 'auto')
    p = int(parameters.get('nnc_p', 2))

    neighbors = KNeighborsClassifier(n_neighbors=n_neighbors,
                                     algorithm=algorithm,
                                     weights=weights,
                                     p=p)

    x_train, x_test, y_train, y_test = train_test_split(input_df, target_df)
    clf_test = neighbors.fit(x_train, y_train)
    acc = get_match_acc(clf_test.predict(x_test), y_test)
    parameters['accuracy'] = acc
    parameters['accuracy_type'] = 'Accuracy [%]'

    neighbors.fit(input_df, target_df)

    return neighbors


def create_k_nearest_neighbors_regressor(input_df, target_df, parameters):
    n_neighbors = int(parameters.get('nnc_k', 5))
    weights = parameters.get('weights', 'uniform')
    algorithm = parameters.get('algorithm', 'auto')
    p = int(parameters.get('nnc_p', 2))
    x_train, x_test, y_train, y_test = train_test_split(input_df, target_df)

    neighbors = KNeighborsRegressor(n_neighbors=n_neighbors,
                                    algorithm=algorithm,
                                    weights=weights,
                                    p=p)

    regr_test = neighbors.fit(x_train, y_train)
    score = round(regr_test.score(x_test, y_test), 4)
    parameters['accuracy'] = score
    parameters['accuracy_type'] = 'R^2'

    neighbors.fit(input_df, target_df)

    return neighbors


def create_nearest_centroid(input_df, target_df, parameters):
    clf = NearestCentroid()

    x_train, x_test, y_train, y_test = train_test_split(input_df, target_df)
    clf_test = clf.fit(x_train, y_train)
    acc = get_match_acc(clf_test.predict(x_test), y_test)
    parameters['accuracy'] = acc
    parameters['accuracy_type'] = 'Accuracy [%]'

    clf.fit(input_df, target_df)

    return clf


def create_support_vector_machine_classifier(input_df, target_df, parameters):
    kernel = parameters.get('svc_kernel', 'rbf')
    degree = int(parameters.get('svc_degree', 3))
    c = parameters.get('svc_C', 1.0)

    clf = svm.SVC(kernel=kernel, degree=degree, C=c)

    x_train, x_test, y_train, y_test = train_test_split(input_df, target_df)
    clf_test = clf.fit(x_train, y_train)
    acc = get_match_acc(clf_test.predict(x_test), y_test)
    parameters['accuracy'] = acc
    parameters['accuracy_type'] = 'Accuracy [%]'

    clf.fit(input_df, target_df)

    return clf


def create_support_vector_machine_regressor(input_df, target_df, parameters):
    kernel = parameters.get('svr_kernel', 'rbf')
    degree = int(parameters.get('svr_degree', 3))

    svm_reg = svm.SVR(kernel=kernel, degree=degree)

    x_train, x_test, y_train, y_test = train_test_split(input_df, target_df)
    regr_test = svm_reg.fit(x_train, y_train)
    score = round(regr_test.score(x_test, y_test), 4)
    parameters['accuracy'] = score
    parameters['accuracy_type'] = 'R^2'

    svm_reg.fit(input_df, target_df)

    return svm_reg

