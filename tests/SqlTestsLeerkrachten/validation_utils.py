def make_check(table, name, sql, op, expected):
    return {
        "table": table,
        "name": name,
        "sql": sql,
        "op": op,
        "expected": expected,
    }


def table(table_name):
    def check(rule, *args):
        if rule == "row_count":
            expected = args[0]
            return make_check(
                table_name,
                "aantal rijen",
                f"SELECT COUNT(*) FROM {table_name}",
                "==",
                expected,
            )

        if rule == "row_count_at_least":
            expected = args[0]
            return make_check(
                table_name,
                "aantal rijen",
                f"SELECT COUNT(*) FROM {table_name}",
                ">",
                expected,
            )
        

        if rule == "row_count_where":
            expected = args[0]
            column_name = args[1]
            lower_bound = int(args[2])
            upper_bound = int(args[3])                  
            return make_check(
                table_name,
                "aantal rijen",
                f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} BETWEEN {lower_bound} AND {upper_bound}",
                "==",
                expected,
            )


        if rule == "not_null":
            column = args[0]
            return make_check(
                table_name,
                f"geen NULL in {column}",
                f"SELECT COUNT(*) FROM {table_name} WHERE {column} IS NULL",
                "==",
                0,
            )


        if rule == "not_null_all":
            columns = args[0]

            if isinstance(columns, str):
                columns = [columns]

            condition = " OR ".join(f"{col} IS NULL" for col in columns)
            column_list = ", ".join(columns)

            return make_check(
                table_name,
                f"geen NULL in {column_list}",
                f"SELECT COUNT(*) FROM {table_name} WHERE {condition}",
                "==",
                0,
            )

        if rule == "no_empty":
            column = args[0]
            return make_check(
                table_name,
                f"geen lege waarden in {column}",
                f"SELECT COUNT(*) FROM {table_name} WHERE TRIM({column}) = ''",
                "==",
                0,
            )

        if rule == "no_empty_all":
            columns = args[0]

            if isinstance(columns, str):
                columns = [columns]

            condition = " OR ".join(f"{col} IS NULL" for col in columns)
            column_list = ", ".join(columns)

            return make_check(
                table_name,
                f"geen lege waarden in {column_list}",
                f"SELECT COUNT(*) FROM {table_name} WHERE {condition}",
                "==",
                0,
            )
        

        if rule == "unique":
            column = args[0]
            return make_check(
                table_name,
                f"unieke waarden in {column}",
                f"SELECT COUNT(*) - COUNT(DISTINCT {column}) FROM {table_name}",
                "==",
                0,
            )

        if rule == "unique_key":

            columns = args[0]

            if isinstance(columns, str):
                columns = [columns]

            column_list = ", ".join(columns)

            return make_check(
                table_name,
                f"unieke sleutel op {column_list}",
                f"""
                SELECT COUNT(*)
                FROM (
                    SELECT {column_list}
                    FROM {table_name}
                    GROUP BY {column_list}
                    HAVING COUNT(*) > 1
                ) duplicates
                """,
                "==",
                0,
            )

        if rule == "fk_valid":

            local_column = args[0]
            ref_table = args[1]
            ref_column = args[2]

            return make_check(
                table_name,
                f"foreign key geldig: {local_column} -> {ref_table}.{ref_column}",
                f"""
                SELECT COUNT(*)
                FROM {table_name} t
                LEFT JOIN {ref_table} r
                    ON t.{local_column} = r.{ref_column}
                WHERE t.{local_column} IS NOT NULL
                AND r.{ref_column} IS NULL
                """,
                "==",
                0,
            )

        raise ValueError(f"Onbekende rule: {rule}")

    return check

def join_avg_sql_like(avg_column, fact_table, dim_table, fact_key, dim_key, filter_column):
    return f"""
        SELECT AVG({avg_column})
        FROM {fact_table} f
        JOIN {dim_table} d
            ON f.{fact_key} = d.{dim_key}
        WHERE d.{filter_column} LIKE ?
    """


def join_count_sql_like(table_right, table_left, right_key, left_key, left_name_column):
    return f"""
        SELECT COUNT(*)
        FROM {table_right} r
        JOIN {table_left} l
            ON r.{right_key} = l.{left_key}
        WHERE l.{left_name_column} LIKE ?
    """

def join_count_sql_like_between(table_right, table_left, right_key, left_key, left_name_column, between_name_column):
    return f"""
        SELECT COUNT(*)
        FROM {table_right} r
        JOIN {table_left} l
            ON r.{right_key} = l.{left_key}
        WHERE l.{left_name_column} LIKE ? AND r.{between_name_column} BETWEEN ? AND ?
    """


def join_sum_sql_like_between(table_right, table_left, right_key, left_key, sum_column, left_name_column, between_name_column):
    return f"""
        SELECT SUM({sum_column})
        FROM {table_right} r
        JOIN {table_left} l
            ON r.{right_key} = l.{left_key}
        WHERE l.{left_name_column} LIKE ? AND r.{between_name_column} BETWEEN ? AND ?
    """