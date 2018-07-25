"""
Execution utils
"""


def find_and_sort_by_first_element_of_list(collection, match, project, sort_var_path):
    """
    Assuming we have a lot of documents (e.g devices_db),
    each of them has a list of objects (e.g. tags),
    each of them has a specific value (e.g. data.id)

    and we want to sort by it.
    MongoDB sort function will not work on lists (tags.data.id) so we need to make this a single var.
    :param collection: mongodb collection
    :param match: a match criteria (what you would give to collection.find([THIS]))
    :param project: project criteria (what you would give to collection.find({}, project=[THIS])
    :param sort_var_path: what to sort by (must be a list), e.g. "tags.data.general_info_last_success_execution"
    :return: a mongodb cursor and its length (cursor, length)
    """

    return collection.aggregate(
        [
            {
                "$match": match
            },
            {
                "$project": project
            },
            {
                "$addFields":
                    {
                        "sort_criteria":
                            {
                                "$arrayElemAt":
                                    [
                                        f"${sort_var_path}",
                                        0
                                    ]
                            }
                    }
            },
            {
                "$sort":
                    {
                        "sort_criteria": 1
                    }
            }
        ],
        allowDiskUse=True
    ), collection.find(match).count()
