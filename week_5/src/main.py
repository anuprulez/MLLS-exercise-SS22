import os
import sys
import pandas as pd
import numpy as np
import json
import networkx as nx
import matplotlib.pyplot as plt

import torch
from torch_geometric.nn import MessagePassing
from torch_geometric.utils import add_self_loops, degree
from torch_geometric.nn import knn_graph
from torch_geometric.data import Data
from torch_geometric.utils import to_networkx
from torch.nn import Linear
from torch_geometric.nn import GCNConv


local_path = "../week_5/"
cancer_names = ["blca", "brca", "coad", "hnsc", "ucec"]

# https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7998488/


def visualize_graph(G, color):
    plt.figure(figsize=(7,7))
    plt.xticks([])
    plt.yticks([])
    nx.draw_networkx(G, pos=nx.spring_layout(G, seed=42), with_labels=False,
                     node_color=color, cmap="Set2")
    plt.show()


def visualize_embedding(h, color, epoch=None, loss=None):
    plt.figure(figsize=(7,7))
    plt.xticks([])
    plt.yticks([])
    h = h.detach().cpu().numpy()
    plt.scatter(h[:, 0], h[:, 1], s=140, c=color, cmap="Set2")
    if epoch is not None and loss is not None:
        plt.xlabel(f'Epoch: {epoch}, Loss: {loss.item():.4f}', fontsize=16)
    plt.show()


class GCN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        torch.manual_seed(1234)
        self.conv1 = GCNConv(12, 4)
        self.conv2 = GCNConv(4, 4)
        self.conv3 = GCNConv(4, 2)
        self.classifier = Linear(2, 2)

    def forward(self, x, edge_index):
        h = self.conv1(x, edge_index)
        h = h.tanh()
        h = self.conv2(h, edge_index)
        h = h.tanh()
        h = self.conv3(h, edge_index)
        h = h.tanh()  # Final GNN embedding space.
        
        # Apply a final (linear) classifier.
        out = self.classifier(h)

        return out, h


def load_node_csv(path, index_col, encoders=None, **kwargs):
    df = pd.read_csv(path, index_col=index_col, header=None)
    mapping = {index: i for i, index in enumerate(df.index.unique())}
    x = df.iloc[:, 0:]
    #print(x)
    return x, mapping


def read_files():
    final_path = cancer_names[0] + "/"
    driver = pd.read_csv(final_path + "drivers", header=None)
    gene_features = pd.read_csv(final_path + "gene_features", header=None)
    links = pd.read_csv(final_path + "links", header=None)
    passengers = pd.read_csv(final_path + "passengers", header=None)

    print(driver)
    print("----")
    print(gene_features)
    print("----")
    print(links)
    print("----")
    print(passengers)
    print("----")
    driver_gene_list = driver[0].tolist()
    passenger_gene_list = passengers[0].tolist()
    
    x, mapping = load_node_csv(final_path + "gene_features", 0)
    y = torch.zeros(x.shape[0], dtype=torch.long)
    y[:] = -1

    driver_ids = driver.replace({0: mapping})
    passenger_ids = passengers.replace({0: mapping})

    # driver = 1, passenger = 0
    y[driver_ids[0].tolist()] = 1
    y[passenger_ids[0].tolist()] = 0

    print(y, y.shape)

    print("Saving mapping...")
    with open('gene_mapping.json', 'w') as outfile:
        outfile.write(json.dumps(mapping))

    print("replacing gene ids")
    links = links[:500]
    re_links = links.replace({0: mapping})
    re_links = re_links.replace({1: mapping})
    print(re_links)

    links_mat = re_links.to_numpy()

    # create data object
    x = x.loc[:, 1:]
    x = x.to_numpy()
    x = torch.tensor(x, dtype=torch.float)
    edge_index = torch.tensor(links_mat, dtype=torch.long) 
    data = Data(x=x, edge_index=edge_index.t().contiguous())

    #print(gene_features[0])
    print("create mask...")
    driver_gene_list.extend(passenger_gene_list)
    tr_mask_drivers = gene_features[0].isin(driver_gene_list)
    tr_mask_drivers = torch.tensor(tr_mask_drivers, dtype=torch.bool)
    data.train_mask = tr_mask_drivers
    data.y = y

    print(data)

    # plot original graph
    G = to_networkx(data, to_undirected=True)
    visualize_graph(G, color=data.y)

    sys.exit()

    model = GCN()

    print(model)
    criterion = torch.nn.CrossEntropyLoss()  # Define loss criterion.
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)  # Define optimizer.

    for epoch in range(2000):
        loss, h = train(data, optimizer, model, criterion)
        if epoch % 10 == 0:
            print("Loss after {} epochs: {}".format(str(epoch), str(loss)))


def train(data, optimizer, model, criterion):
    optimizer.zero_grad()  # Clear gradients.
    out, h = model(data.x, data.edge_index)  # Perform a single forward pass.
    loss = criterion(out[data.train_mask], data.y[data.train_mask])  # Compute the loss solely based on the training nodes.
    loss.backward()  # Derive gradients.
    optimizer.step()  # Update parameters based on gradients.
    return loss, h


if __name__ == "__main__":
    read_files()
