import sys
import pandas as pd
import numpy as np
import pickle
from rdkit import Chem
from mordred import Calculator, descriptors
from tensorflow.keras import models

Factor = float(1/1000.0)

def calc_descriptors(mols, name):

  len1 = len(mols)
  features = []
  for i in range(len1):
    des1 = calc.pandas([mols[i]])
    values = des1.values.tolist()
    features.append(values[0])

  features = pd.DataFrame(features,columns=name)
  features = features._get_numeric_data()
  return features

if __name__ == '__main__':

# Input of ILs to be predicted
  narg = len(sys.argv)
  if narg < 2:
    print("Usage: prediction.py excelfile ")
    print("       excelfile: excel containing smiles and names of ionic liquids in column-wise")
    exit()

  source1 = sys.argv[1]
  full_data = pd.read_excel(source1)
  pairs_name = full_data['NAME']
  melting_points = full_data['TM']
  smiles_pairs = full_data.iloc[:,0].str.split('.', expand=True, n=1)
  smiles_ac_pairs = smiles_pairs.rename(columns={0: 'cation', 1: 'anion'})
  cation = smiles_ac_pairs['cation']
  cation_mols = [Chem.MolFromSmiles(x) for x in cation]
  anion = smiles_ac_pairs['anion']
  anion_mols = [Chem.MolFromSmiles(x) for x in anion]
  exp_mp = np.array(melting_points) + 273.15

# descriptors needed and zs_scaler
  source2 = './for-external.pkl'
  with open(source2,'rb') as f1: 
    zs_scaler = pickle.load(f1)
    col_descriptors = pickle.load(f1)

# generate Mordred descriptors
  calc = Calculator(descriptors, ignore_3D=True)
  smi1 = 'c1ccccc1'
  mol1 = Chem.MolFromSmiles(smi1)
  des1 = calc.pandas([mol1])
  descriptors_name = des1.keys().tolist()
  cation_descriptors = calc_descriptors(cation_mols, descriptors_name)
  anion_descriptors = calc_descriptors(anion_mols, descriptors_name)

  pred_cation = cation_descriptors[col_descriptors]
  pred_anion  = anion_descriptors[col_descriptors]

# prepare input pairs
  ndes = 209
  N_cation = pred_cation.values.tolist()
  N_cation = np.array(N_cation)
  N_anion  = pred_anion.values.tolist()
  N_anion  = np.array(N_anion)
  N_pairs  = np.concatenate([N_cation,N_anion],axis=1)
  N_pairs  = zs_scaler.transform(N_pairs)

  test_x1, test_x2 = N_pairs[:,:ndes], N_pairs[:,ndes:]
  
# load the trained models (5 models)
  n_folds = 5
  members = list()
  ifold = 0
  for i in range(n_folds):
    fname = './model_'+str(ifold)+'.keras'
    model = models.load_model(fname)
    members.append(model)
    ifold += 1

  ypre, test_scores = list(), list()
  for i in range(n_folds):
    predict = members[i].predict([test_x1,test_x2])
    predict = predict.flatten()
    ypre.append(predict)

  ypre = np.array(ypre)
  means =  [ np.mean(ypre[:,i]) for i in range(ypre.shape[1]) ]
  means = np.array(means)/Factor

  print(f'     ILs                Predicted(Tm)   Exp(Tm)')
  for i in range(len(means)): 
    print(f'    {pairs_name[i]:20s} {means[i]:8.1f}   {exp_mp[i]:8.1f}')
 
